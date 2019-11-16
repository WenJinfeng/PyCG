from pycg.machinery.pointers import NamePointer, LiteralPointer

class DefinitionManager(object):
    RETURN_NAME     = "<**RETURN**>"

    def __init__(self):
        self.defs = {}

    def create(self, ns, def_type):
        if not ns or not isinstance(ns, str):
            raise DefinitionError("Invalid namespace argument")
        if not def_type in Definition.types:
            raise DefinitionError("Invalid def type argument")
        if self.get(ns):
            raise DefinitionError("Definition already exists")

        self.defs[ns] = Definition(ns, def_type)
        return self.defs[ns]

    def assign(self, ns, defi):
        self.defs[ns] = Definition(ns, defi.get_type())
        self.defs[ns].merge(defi)

        # if it is a function def, we need to create a return pointer
        if defi.is_function_def():
            return_ns = "{}.{}".format(ns, self.RETURN_NAME)
            self.defs[return_ns] = Definition(return_ns, Definition.NAME_DEF)
            self.defs[return_ns].get_name_pointer().add("{}.{}".format(defi.get_ns(), self.RETURN_NAME))

        return self.defs[ns]

    def get(self, ns):
        if ns in self.defs:
            return self.defs[ns]

    def handle_function_def(self, parent_ns, fn_name):
        full_ns = "{}.{}".format(parent_ns, fn_name)
        defi = self.get(full_ns)
        if not defi:
            defi = self.create(full_ns, Definition.FUN_DEF)

        return_ns = "{}.{}".format(full_ns, self.RETURN_NAME)
        self.create(return_ns, Definition.NAME_DEF)

        return defi

    def transitive_closure(self):
        closured = {}
        def dfs(defi):
            name_pointer = defi.get_name_pointer()
            new_set = set()
            # bottom
            if not name_pointer.get():
                new_set.add(defi.get_ns())

            for name in name_pointer.get():
                new_set = new_set.union(dfs(self.defs[name]))

            closured[defi.get_ns()] = new_set
            return closured[defi.get_ns()]

        for ns, current_def in self.defs.items():
            dfs(current_def)

        return closured

    def complete_definitions(self):
        # THE MOST expensive part of this tool's process
        # TODO: IMPROVE COMPLEXITY
        def update_pointsto_args(pointsto_args, arg):
            changed_something = False
            for pointsto_arg in pointsto_args:
                if not self.defs.get(pointsto_arg, None):
                    continue
                pointsto_arg_def = self.defs[pointsto_arg].get_name_pointer()
                # sometimes we may end up with a cycle
                if pointsto_arg in arg:
                    arg.remove(pointsto_arg)

                for item in arg:
                    if not item in pointsto_arg_def.get():
                        changed_something = True
                    # HACK: this check shouldn't be needed
                    # if we remove this the following breaks:
                    # x = lambda x: x + 1
                    # x(1)
                    # since on line 184 we don't discriminate between literal values and name values
                    if not self.defs.get(item, None):
                        continue
                    pointsto_arg_def.add(item)
            return changed_something

        for i in range(len(self.defs)):
            changed_something = False
            for ns, current_def in self.defs.items():
                # the name pointer of the definition we're currently iterating
                current_name_pointer = current_def.get_name_pointer()
                # iterate the names the current definition points to items
                for name in current_name_pointer.get():
                    # get the name pointer of the points to name
                    pointsto_name_pointer = self.defs[name].get_name_pointer()
                    # iterate the arguments of the definition we're currently iterating
                    for arg_name, arg in current_name_pointer.get_args().items():
                        pos = current_name_pointer.get_pos_of_name(arg_name)
                        if not pos is None:
                            pointsto_args = pointsto_name_pointer.get_pos_arg(pos)
                            if not pointsto_args:
                                pointsto_name_pointer.add_pos_arg(pos, None, arg)
                                continue
                        else:
                            pointsto_args = pointsto_name_pointer.get_arg(arg_name)
                            if not pointsto_args:
                                pointsto_name_pointer.add_arg(arg_name, arg)
                                continue
                        changed_something = changed_something or update_pointsto_args(pointsto_args, arg)

            if not changed_something:
                break


class Definition(object):
    FUN_DEF     = "FUNCTIONDEF"
    NAME_DEF    = "NAMEDEF"
    MOD_DEF     = "MODULEDEF"
    types       = [FUN_DEF, MOD_DEF, NAME_DEF]

    def __init__(self, fullns, def_type):
        self.fullns = fullns
        self.points_to = {
            "lit": LiteralPointer(),
            "name": NamePointer()
        }
        self.def_type = def_type

    def get_type(self):
        return self.def_type

    def is_function_def(self):
        return self.def_type == self.FUN_DEF

    def get_lit_pointer(self):
        return self.points_to["lit"]

    def get_name_pointer(self):
        return self.points_to["name"]

    def get_name(self):
        return self.fullns.split(".")[-1]

    def get_ns(self):
        return self.fullns

    def merge(self, to_merge):
        for name, pointer in to_merge.points_to.items():
            self.points_to[name].merge(pointer)

class DefinitionError(Exception):
    pass
