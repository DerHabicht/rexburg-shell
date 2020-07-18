import subprocess
import yaml
from os import remove
from time import sleep
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class Version(yaml.YAMLObject):
    yaml_loader = yaml.SafeLoader
    yaml_tag = u'!Version'

    def __init__(self, version, date, author, remarks):
        self.version = version
        self.date = date
        self.author = author
        self.remarks = remarks

    def __str__(self):
        return (
            f'{self.version}:\n'
            f'        Author:  {self.author}\n'
            f'        Date:    {self.date}\n'
            f'        Remarks: {self.remarks}\n'
        )

    def vhistory_entry(self):
        return f'    \\vhEntry{{{self.version}}}{{{self.date}}}{{{self.author}}}{{{self.remarks}}}'


class BuildConfig(yaml.YAMLObject):
    yaml_loader = yaml.SafeLoader
    yaml_tag = u'!BuildConfig'

    def __init__(self, top_level, inputs, version_history):
        self.top_level = top_level
        self.inputs = inputs
        self.version_history = version_history

    def __str__(self):
        inputs = '\n'.join([f'    {i}' for i in self.inputs])
        vhistory = '\n'.join([f'    {v}' for v in self.version_history])
        return '\n'.join(['Inputs:', inputs, 'Version History:', vhistory])

    def version_history_tex(self):
        entries = [v.vhistory_entry() for v in self.version_history]
        return '\n'.join([r'\begin{versionhistory}', '\n'.join(entries), r'\end{versionhistory}', ''])

    def inputs_tex(self):
        return '\n'.join([f'\\input{{{i}}}' for i in self.inputs])


class LaTeXDocument:
    def __init__(self, slug, project, build_config):
        self.slug = slug
        self.project = project
        self.build_config = build_config

    def __str__(self):
        return f'{self.project}{self.build_config}'

    def _parse_content(self):
        for i in self.build_config.inputs:
            subprocess.run(['pandoc',
                            f'--top-level-division={self.build_config.top_level}',
                            '-o',
                            f'{self.project.latex_path}/{i}.tex',
                            f'{self.project.content_path}/{i}.md'])

    def _build_template(self, for_print=False):
        with open(f'{self.project.latex_path}/{self.slug}.template', 'r') as file:
            template = file.read()

        if for_print:
            template = template.replace(r'%!{PRINT}', r'\printtrue')
        else:
            template = template.replace(r'%!{PRINT}', r'\printfalse')

        template = template.replace(r'%!{VERSION_HISTORY}', self.build_config.version_history_tex())
        template = template.replace(r'%!{INPUTS}', self.build_config.inputs_tex())

        with open(f'{self.project.latex_path}/{self.slug}.tex', 'w') as file:
            file.write(template)

    def _build_document(self):
        subprocess.run(['pdflatex', '-halt-on-error', f'{self.slug}.tex'], cwd=self.project.latex_path)
        subprocess.run(['makeglossaries', self.slug], cwd=self.project.latex_path)
        subprocess.run(['biber', self.slug], cwd=self.project.latex_path)
        subprocess.run(['makeindex', self.slug], cwd=self.project.latex_path)
        subprocess.run(['pdflatex', '-halt-on-error', f'{self.slug}.tex'], cwd=self.project.latex_path)
        subprocess.run(['pdflatex', '-halt-on-error', f'{self.slug}.tex'], cwd=self.project.latex_path)

    def make(self, for_print=False, to_pdf=False):
        self._parse_content()
        self._build_template(for_print)
        if to_pdf:
            self._build_document()

    def clean(self):
        remove(f'{self.project.latex_path}/{self.slug}.tex')

        for i in self.build_config.inputs:
            try:
                remove(f'{self.project.latex_path}/{i}.tex')
            except FileNotFoundError:
                pass

    @staticmethod
    def load_document(project, all_projects):
        try:
            p = all_projects[project]
        except KeyError:
            raise KeyError(f'{project} is not a valid project identifier. Valid projects are {all_projects}')

        try:
            c = load_config(p.content_path)
        except FileNotFoundError:
            raise FileNotFoundError(f'Project {project} does not have a valid build.yml file.')

        return LaTeXDocument(project, p, c)


class BuildWatch:
    def __init__(self, document, to_pdf=False, for_print=False):
        self.document = document
        self.observer = Observer()
        self.to_pdf = to_pdf
        self.for_print = for_print

    def run(self):
        event_handler = BuildWatchEventHandler(self.document)
        self.observer.schedule(event_handler, self.document.project.content_path, recursive=True)
        self.observer.start()
        try:
            while True:
                sleep(5)
        except KeyboardInterrupt:
            self.observer.stop()


class BuildWatchEventHandler(FileSystemEventHandler):
    def __init__(self, document, to_pdf=False, for_print=False):
        super().__init__()
        self.document = document
        self.to_pdf = to_pdf
        self.for_print = for_print
        self.paths = [f'{document.project.content_path}/{file}.md'
                      for file in document.build_config.inputs]

    def on_modified(self, event):
        if event.src_path in self.paths:
            print(f'Change in {event.src_path}. Rebuilding...')
            self.document.make(for_print=self.for_print, to_pdf=self.to_pdf)


def load_config(project_path):
    with open(f'{project_path}/build.yml', 'r') as file:
        raw = file.read()

    return yaml.safe_load(raw)
