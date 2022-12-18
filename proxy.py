from socket import *
import sys
import os
import shutil
import select

cacheDir = os.path.join(os.path.dirname(__file__), 'cache')
# os.path.dirname() method in Python is used to get the directory name from the specified path
#C:\Users\stell\eclipse-workspace\httplab\venv\cache

# For WINDOWS: can't keyboard interrupt while the program is in a blocking call
# Workaround is to timeout a blocking call every timeLeft seconds so the program can
# respond to any SIGINT or SIGKILL signals
# Shouldn't be a problem on Mac or Linux
# Additional note for WINDOWS: select.select() only works on sockets, so waitable should be a socket
def wait_interruptible(waitable, timeLeft):
    while True:
        ready = select.select([waitable], [], [], timeLeft)
        if len(ready[0]) > 0:
            return

# interruptible versions of accept(), recv(), readline(), read()
def interruptible_accept(socket):
    wait_interruptible(socket, 5)
    return socket.accept()

def interruptible_recv(socket, nbytes):
    wait_interruptible(socket, 5)
    return socket.recv(nbytes)

def interruptible_readline(fileObj):
    wait_interruptible(fileObj, 5)
    return fileObj.readline()
#a file method that helps to read one complete line from the given file

def interruptible_read(fileObj, nbytes=-1):
    wait_interruptible(fileObj, 5)
    return fileObj.read(nbytes)
#The read() method returns the specified number of bytes from the file.
# Default is -1 which means the whole file.


# Read an HTTP message from a socket file object and parse it
# sockf: Socket file object to read from
# Returns: (headline: str, [(header: str, header_value: str)])
def parse_http_headers(sockf):
    # Read the first line from the HTTP message
    # This will either be the Request Line (request) or the Status Line (response)
    headline = interruptible_readline(sockf).decode().strip()
    # def interruptible_readline(fileObj):
    #     wait_interruptible(fileObj, 5)
    # return fileObj.readline()

    # Set up list for headers
    headers = []
    while True:
        # Read a line at a time
        header = interruptible_readline(sockf).decode()
        # If it's the empty line '\r\n', it's the end of the header section
        if len(header.rstrip('\r\n')) == 0:
            break

        # Partition header by colon
        headerPartitions = header.partition(':')

        # Skip if there's no colon
        if headerPartitions[1] == '':
            continue

        headers.append((headerPartitions[0].strip(), headerPartitions[2].strip()))

    return(headline, headers)

#(first line of http msg, [(host, xxx),(user-agent, xxx)...])

# Forward a server response to the client and save to cache
# sockf: Socket file object connected to server
# fileCachePath: Path to cache file
# clisockf: Socket file object connected to client
def forward_and_cache_response(sockf, fileCachePath, clisockf):

    # forward_and_cache_response(fileobj, fileCachePath, cliSock_f)
    #forward means forward to client
    cachef = None

    # Create the intermediate directories to the cache file
    if fileCachePath is not None:
        os.makedirs(os.path.dirname(fileCachePath), exist_ok=True)
        # Open/create cache file
        cachef = open(fileCachePath, 'w+b')

    try:
        # Read response from server
        statusLine, headers = parse_http_headers(sockf)
        print(f'statusline: {statusLine}')
        print(f'headers: {headers}')

        # Filter out the Connection header from the server
        headers = [h for h in headers if h[0] != 'Connection']
        # Replace with our own Connection header
        # We will close all connections after sending the response.
        # This is an inefficient,  single-threaded proxy!
        headers.append(('Connection', 'close'))
        # Fill in start.
        message = statusLine + '\r\n'
        for x in headers:
            message = message + x[0] + ": " + x[1] + '\r\n'

        message = message + '\r\n'
        print(f'message to client: {message}')

        clisockf.write(message.encode())

        print('message sent to client')
        # Fill in end.
    except Exception as e:
        print(e)
    finally:
        if cachef is not None:
            cachef.close()

# Forward a client request to a server
# sockf: Socket file object connected to server
# requestUri: The request URI to request from the server
# hostn: The Host header value to include in the forwarded request
# origRequestLine: The Request Line from the original client request
# origHeaders: The HTTP headers from the original client request

#forward_request(fileobj, f'/{filename.partition("/")[2]}', hostn, requestLine, requestHeaders)


def forward_request(sockf, requestUri, hostn, origRequestLine, origHeaders):
    # Filter out the original Host header and replace it with our own
    headers = [h for h in origHeaders if h[0] != 'Host']
    headers.append(('Host', hostn))
    # Send request to the server

    # forward_request(fileobj, f'/{filename.partition("/")[2]}', hostn, requestLine, requestHeaders)
    # requestHeaders: [('Host', 'localhost:5000'), ('User-Agent', 'python-requests/2.28.1'),('Accept-Encoding', 'gzip, deflate'), ('Accept', '*/*'), ('Connection', 'keep-alive')]
    # requestLine: GET http://localhost:5000/test-basic-200 HTTP/1.1

    # Fill in start.
    message = origRequestLine + '\r\n'
    for x in headers:
            message = message + x[0] + ": " + x[1] + '\r\n'

    message = message + '\r\n'

    print(f'message: {message}')
    sockf.write(message.encode('utf-8'))
    print('complete writing')
    # Fill in end.

#   requestLine, requestHeaders = parse_http_headers(cliSock_f)
#   requestLine = cliSock_f.readLine().decode().strip()
# #a file method that helps to read one complete line from the given file


def proxyServer(port):
    print(cacheDir)
    if os.path.isdir(cacheDir):
        shutil.rmtree(cacheDir)
    # Create a server socket, bind it to a port and start listening
    # Fill in start.
    tcpSerSock = socket(AF_INET, SOCK_STREAM)
    tcpSerSock.bind(("",port))
    tcpSerSock.listen(5)
    # Fill in end.

    tcpCliSock = None
    try:
        while 1:
            # Start receiving data from the client
            print('Ready to serve...')
            tcpCliSock, addr = interruptible_accept(tcpSerSock)
            # return tcpSerSock.accept()

            print('Received a connection from:', addr)
            cliSock_f = tcpCliSock.makefile('rwb', 0)

            # Read and parse request from client
            requestLine, requestHeaders = parse_http_headers(cliSock_f)
            # requestLine = interruptible_readline(cliSock_f).decode().strip()
            print(f'original requestLine: {requestLine}')

            if len(requestLine) == 0:
                continue

            # Extract the request URI from the given message
            requestUri = requestLine.split()[1]

            # if a scheme(like GETFILE) is included, split off the scheme, otherwise split off a leading slash
            # GETFILE GET /path/to/file.pdf\r\n\r\n
            # http://github.com/pic.jpg
            # xxx, http://, github.com/pic.jpg
            uri_parts = requestUri.partition('http://')
            if uri_parts[1] == '':
                filename = requestUri.partition('/')[2]
            else:
                filename = uri_parts[2]

            print(f'filename: {filename}')
            # when using an "f" in front of a string,
            # all the variables inside curly brackets are read and replaced by there value.

            if len(filename) > 0:
                # Compute the path to the cache file from the request URI
                # Change for Part Three
                fileCachePath = None
                cached = False

                print(f'fileCachePath: {fileCachePath}')

                # Check whether the file exists in the cache
                if fileCachePath is not None and cached:
                    # Read response from cache and transmit to client
                    # Fill in start.
                    # Fill in end.
                    print('Read from cache')
                else:
                    # Create a socket on the ProxyServer
                    # Fill in start.             # Fill in end.
                    c = socket(AF_INET, SOCK_STREAM)

                    hostn = filename.partition('/')[0]
                    print(f'hostn: {hostn}')

                    # github.com/pic.jpg

                    try:
                        # Connect to the socket
                        # Fill in start.
                        c.connect(('localhost', 5000))
                        # Fill in end.

                        # Create a temporary file on this socket and ask port 80 for the file requested by the client
                        fileobj = c.makefile('rwb', 0)

                        print(f'/{filename.partition("/")[2]}')
                        print(f'requestLine: {requestLine}')
                        print(f'requestHeaders: {requestHeaders}')

                        forward_request(fileobj, f'/{filename.partition("/")[2]}', hostn, requestLine, requestHeaders)
                        # requestLine: GET http://localhost:5000/test-basic-200 HTTP/1.1

                        # Read the response from the server, cache, and forward it to client
                        forward_and_cache_response(fileobj, fileCachePath, cliSock_f)
                    except Exception as e:
                        print(e)
                    finally:
                        c.close()
            tcpCliSock.close()
    except KeyboardInterrupt:
        pass

    # Close the server socket and client socket
    # Fill in start.
    tcpCliSock.close()
    tcpCliSock.close()
    # Fill in end.
    sys.exit()

if __name__ == "__main__":
    proxyServer(8888)
