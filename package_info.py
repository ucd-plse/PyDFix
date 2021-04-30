class PackageInfo:
    def __init__(self, name):
        self._name = name
        self._is_pinned = False
        self._version_pinned = None
        self.is_constrained = False
        self._version_constraints = None
        self._version_fetched = None
        self._is_transitive = False
        self._transitive_deps = None

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def version_pinned(self):
        return self._version_pinned

    @version_pinned.setter
    def version_pinned(self, value):
        self._version_pinned = value

    @property
    def is_constrained(self):
        return self._is_constrained

    @is_constrained.setter
    def is_constrained(self, value):
        self._is_constrained = value

    @property
    def version_constraints(self):
        return self._version_constraints

    @version_constraints.setter
    def version_constraints(self, value):
        self._version_constraints = value

    @property
    def version_fetched(self):
        return self._version_fetched

    @version_fetched.setter
    def version_fetched(self, value):
        self._version_fetched = value

    @property
    def is_transitive(self):
        return self._is_transitive

    @is_transitive.setter
    def is_transitive(self, value):
        self._is_transitive = value

    @property
    def transitive_deps(self):
        return self._transitive_deps

    @transitive_deps.setter
    def transitive_deps(self, value):
        self._transitive_deps = value
