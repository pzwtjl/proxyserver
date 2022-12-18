from flask import Flask, render_template_string, abort, request

app = Flask(__name__)
server_string = '3648b005ac698f9ed4d298dd94ba6f39'
not_found_string = '806ad6f4e71d4a992fcd4d17af1ea0c4'
reflect_count_dict = {}

@app.route("/<input_string>")
def reflect(input_string):
    if input_string == not_found_string:
        abort(404)

    if input_string in reflect_count_dict:
        reflect_count_dict[input_string] += 1
    else:
        reflect_count_dict[input_string] = 1

    print(reflect_count_dict)
    return render_template_string('<!doctype html><html><title>Test File</title><p>You provided: {{ input_string }}</p><p>We provided: {{ server_string }}</p></html>', input_string=input_string, server_string=server_string)

@app.route("/post", methods=['POST'])
def reflect_post():
    input_string = request.form['input_string']

    if input_string in reflect_count_dict:
        reflect_count_dict[input_string] += 1
    else:
        reflect_count_dict[input_string] = 1

    print(reflect_count_dict)
    return render_template_string('<!doctype html><html><title>Test File</title><p>You provided: {{ input_string }}</p><p>We provided: {{ server_string }}</p></html>', input_string=input_string, server_string=server_string)

@app.route("/count")
def count():
    return reflect_count_dict
