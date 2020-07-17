import yaml


class Project(yaml.YAMLObject):
    yaml_loader = yaml.SafeLoader
    yaml_tag = u'!Project'

    def __init__(self, name, latex_path, content_path, compendium):
        self.name = name
        self.latex_path = latex_path
        self.content_path = content_path
        self.compendium = compendium

    def __str__(self):
        return (
            f'{self.name}:\n'
            f'    Content path: {self.content_path}\n'
            f'    LaTeX path:   {self.latex_path}\n'
            f'    Included in Compendium? {self.compendium}\n'
        )


class SeagullConfig(yaml.YAMLObject):
    yaml_loader = yaml.SafeLoader
    yaml_tag = u'!SeagullConfig'

    def __init__(self, projects):
        self.projects = projects

    def __getitem__(self, slug):
        return self.projects[slug]

    def __str__(self):
        p = [f'    {k}: {v.name}' for (k, v) in self.projects.items()]
        return '\n'.join(p)


def load_projects():
    with open('seagull.yml', 'r') as file:
        raw = file.read()

    return yaml.safe_load(raw)