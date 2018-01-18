import io
from importlib import import_module
from tempfile import NamedTemporaryFile

from flask import Flask, request, abort, redirect, render_template, send_from_directory


VALID_FUNCTIONS = {
    'partpooling': 'toolbox.generators.partpooling.PartPoolingGenerator',
}
FILE_STORE = '../files/'

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/worklists/')
def redirect_to_default():
    return redirect('/worklists/partpooling/')

@app.route('/worklists/<function>/', methods=['GET', 'POST'])
def worklists(function):
    data = {}
    results = {}
    error = None
    if function in VALID_FUNCTIONS:
        if request.method == 'POST':
            data = request.form.to_dict()
            data['supplied_files'] = {}
            for key, f in request.files.items():
                tf = io.StringIO(f.read().decode('utf-8'))
                data['supplied_files'][key] = tf
            module, class_name = VALID_FUNCTIONS[function].rsplit('.', 1)
            GeneratorClass = getattr(import_module(module), class_name)
            try:
                m = GeneratorClass(**data, write_to=FILE_STORE)
                generated_data = m.generate(data.get('equipment', 'mosquito'))
                results['output_files'] = {fn: f.split('/')[-1] for fn, f in \
                                           generated_data[0].items()}
                results['plates'] = generated_data[2]
                results['other_files'] = {fn: f.split('/')[-1] for fn, f in generated_data[1]}
            except Exception as e:
                error = e
        return render_template('{}.html'.format(function), data=data, results=results, error=error)
    else:
        abort(404)

@app.route('/worklists/download/<filename>/<download_as>/', methods=['GET'])
def get_worklist_file(filename, download_as):
    try:
        return send_from_directory(FILE_STORE, filename, as_attachment=True,
                                   attachment_filename='{}.csv'.format(download_as))
    except Exception as e:
        abort(404)