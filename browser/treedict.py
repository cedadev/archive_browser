# Make a dictionary like structure that is keyed by paths. 
# It stores values that can be retrived using sub-paths.

class TreeDict:
    def __init__(self, sep="/"):
        self._dict = {}
        self.sep = sep
        
    def __repr__(self):
        return repr(self._dict)

    def __len__(self):
        return len(self._dict)

    def clear(self):
        return self._dict.clear()

    def copy(self):
        return self._dict.copy()

    def has_key(self, path):
        path = self._clean_path(path)
        return path in self._dict

    def update(self, *args, **kwargs):
        return self._dict.update(*args, **kwargs)

    def keys(self):
        return self._dict.keys()

    def values(self):
        return self._dict.values()

    def items(self):
        return self._dict.items()

    def pop(self, *args):
        return self._dict.pop(*args)

    def __cmp__(self, dict_):
        return self.__cmp__(self._dict, dict_)

    def __contains__(self, item):
        return item in self._dict

    def __iter__(self):
        return iter(self._dict)

    def __unicode__(self):
        return unicode(repr(self._dict))
        
    def _clean_path(self, path):
        """Make sure a path is clean and absolute."""
        if not path.startswith(self.sep):
            raise ValueError(f"Path must start with '{self.sep}'")
        return path.rstrip(self.sep)

    def __setitem__(self, path, value):
        """store a value for a path"""
        path = self._clean_path(path)
        self._dict[path] = value

    def value(self, path):
        """Get a value for an exact path."""
        path = self._clean_path(path)
        return self._dict.get(path, None)
    
    def __getitem__(self, path):
        """Get a value for a path finding values in parents if needed."""
        path = self._clean_path(path)
        while True:
            if path in self._dict:
                return self._dict[path]
            if self.sep not in path:
                # top of tree
                break
            path = path.rsplit(self.sep, 1)[0]
        return None

    def __delitem__(self, path):
        """remove value from a path"""
        path = self._clean_path(path)
        if path in self._dict:
            del self._dict[path]

            
if __name__ == "__main__":

    tree_store = TreeDict()
    tree_store["/badc/cira"] = 42
    tree_store["/badc/cira/data"] = {"some": "data"}
    tree_store["/badc/xxx"] = 15534
    print(tree_store["/badc/cira"])  # Output: 42
    print(tree_store["/badc"])  # Output: None
    print(tree_store["/badc/cira/data/x/y"]) # Output: 42
    del tree_store["/badc/cira/data"]
    print(tree_store["/badc/cira/data"])  # Output: None
    print(tree_store["/badc/cira/data/x"]) # Output: 42
    print(tree_store["/badc/cira/data"])
    print(tree_store)
    print(tree_store.keys())
    print(tree_store.values())
    print(len(tree_store))
    for path, value in tree_store.items():
        print(path, value)
    tree_store["fff/rrr"] = 9
    
