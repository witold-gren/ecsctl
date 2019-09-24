import oyaml as yaml
from pathlib import Path
from jsonpath_ng import parse
from . import template, exceptions


class FileLoader:

    def __init__(self, file_path):
        self.file_path = file_path

    def load(self):
        path = Path(self.file_path)
        if path.is_dir():
            files = [x for x in path.glob("*.yaml")]
            files.extend([x for x in path.glob("*.yml")])
            file_data = ""
            for item in files:
                f = item.read_text()
                if not f.startswith('---'):
                    file_data += '---\n'
                file_data += f
        else:
            file_data = path.read_text()
        return yaml.load_all(file_data, Loader=yaml.Loader)


class ObjectType:
    __name = parse('metadata.name')
    __tags = parse('metadata.tags')
    __kind = parse('kind')
    __spec = parse('spec')
    __api = parse('apiVersion')

    def __init__(self, cluster, item):
        self.item = item
        self.cluster = cluster
        self.kind = None
        self.name = None
        self.spec = None
        self.tags = None
        self.ID = None
        self.template = None
        self._load_data()

    def _load_data(self):
        self.kind = self._get_value(self.__kind.find(self.item), 'name')
        self.name = self._get_value(self.__name.find(self.item), 'kind')
        self.spec = self._get_value(self.__spec.find(self.item), 'spec')
        self.tags = self.__tags.find(self.item)[0].value if self.__tags.find(self.item) else []
        metadata = self.item.get('metadata')
        metadata.pop('name', None)
        self.metadata = metadata
        self.ID = "{}: {}".format(self.kind, self.name)
        if self._get_value(self.__api.find(self.item), 'apiVersion') != 'v1':
            raise exceptions.ObjectTypeException('Currently we support only `apiVersion: v1`')

    @staticmethod
    def _get_value(found_elements, kind):
        try:
            return found_elements[0].value
        except IndexError:
            raise exceptions.ObjectTypeException('`{}` - this value doesn\'t exist.'.format(kind))

    def get_template(self):
        func = getattr(template, self.kind)
        self.template = func(
            name=self.name,
            tags=self.tags,
            yaml=self.spec,
            cluster=self.cluster,
            metadata=self.metadata)
        return self.template

    def show_response(self, resp):
        if not self.template:
            self.get_template()
        return self._get_value(parse(self.template.response).find(resp), self.template.response)
