import subprocess
import yaml
from os import remove


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

    top_level = 'chapter'
    tlp = 'white'
    inputs = None
    annexes = None
    version_history = None

    def __init__(self, top_level, tlp, inputs, annexes, version_history):
        self.top_level = top_level
        self.tlp = tlp
        self.inputs = inputs
        self.annexes = annexes
        self.version_history = version_history

    def __str__(self):
        inputs = '\n'.join([f'    {i}' for i in self.inputs]) if self.inputs else ''
        annexes = '\n'.join([f'    {i}' for i in self.annexes]) if self.annexes else ''
        vhistory = '\n'.join([f'    {v}' for v in self.version_history]) if self.version_history else ''
        return '\n'.join(['Inputs:', inputs, 'Annexes:', annexes, 'Version History:', vhistory])

    def recent_version_date(self):
        if self.version_history:
            return self.version_history[-1].date
        else:
            raise NotImplementedError('Attempted to insert date into document without a version history.')

    def version_history_tex(self):
        if self.version_history:
            entries = [v.vhistory_entry() for v in self.version_history]
            return '\n'.join([r'\begin{versionhistory}', '\n'.join(entries), r'\end{versionhistory}', ''])
        else:
            return ''

    def inputs_tex(self):
        if self.inputs:
            return '\n'.join([f'\\include{{{i}}}' for i in self.inputs])
        else:
            return ''

    def annexes_tex(self):
        if self.annexes:
            return '\n'.join([f'\\include{{{i}}}' for i in self.annexes])
        else:
            return ''


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
                            '--filter=pandoc-theorem-exe',
                            f'--top-level-division={self.build_config.top_level}',
                            '-o',
                            f'{self.project.latex_path}/{i}.tex',
                            f'{self.project.content_path}/{i}.md'])

        if self.build_config.annexes:
            for i in self.build_config.annexes:
                subprocess.run(['pandoc',
                                '--filter=pandoc-theorem-exe',
                                f'--top-level-division={self.build_config.top_level}',
                                '-o',
                                f'{self.project.latex_path}/{i}.tex',
                                f'{self.project.content_path}/{i}.md'])

    def _build_template(self, for_print=False):
        try:
            with open(f'{self.project.latex_path}/{self.slug}.template', 'r') as file:
                template = file.read()
        except FileNotFoundError:
            print(f'ERROR: {self.project.latex_path}/{self.slug}.template not found.')
            exit(1)

        if for_print:
            template = template.replace(r'%!{PRINT}', r'\printtrue')
        else:
            template = template.replace(r'%!{PRINT}', r'\printfalse')

        template = template.replace(r'%!{TLP}', self.build_config.tlp)

        template = template.replace(r'%!{DATE}', self.build_config.recent_version_date())
        template = template.replace(r'%!{VERSION_HISTORY}', self.build_config.version_history_tex())
        template = template.replace(r'%!{INPUTS}', self.build_config.inputs_tex())
        template = template.replace(r'%!{ANNEXES}', self.build_config.annexes_tex())

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
        try:
            remove(f'{self.project.latex_path}/{self.slug}.tex')
        except FileNotFoundError:
            pass
        try:
            remove(f'{self.project.latex_path}/{self.slug}.log')
        except FileNotFoundError:
            pass
        try:
            remove(f'{self.project.latex_path}/{self.slug}.out')
        except FileNotFoundError:
            pass
        try:
            remove(f'{self.project.latex_path}/{self.slug}.aux')
        except FileNotFoundError:
            pass
        try:
            remove(f'{self.project.latex_path}/{self.slug}.pdf')
        except FileNotFoundError:
            pass

        if self.build_config.inputs:
            for i in self.build_config.inputs:
                try:
                    remove(f'{self.project.latex_path}/{i}.tex')
                except FileNotFoundError:
                    pass
                try:
                    remove(f'{self.project.latex_path}/{i}.aux')
                except FileNotFoundError:
                    pass

        if self.build_config.annexes:
            for i in self.build_config.annexes:
                try:
                    remove(f'{self.project.latex_path}/{i}.tex')
                except FileNotFoundError:
                    pass
                try:
                    remove(f'{self.project.latex_path}/{i}.aux')
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


def load_config(project_path):
    with open(f'{project_path}/build.yml', 'r') as file:
        raw = file.read()

    return yaml.safe_load(raw)
