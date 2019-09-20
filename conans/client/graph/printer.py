from collections import OrderedDict


from conans.client.graph.graph import BINARY_SKIP, RECIPE_CONSUMER, RECIPE_VIRTUAL,\
    RECIPE_EDITABLE
from conans.client.output import Color
from conans.model.ref import PackageReference


def _get_python_requires(conanfile):
    result = set()
    for _, py_require in getattr(conanfile, "python_requires", {}).items():
        result.add(py_require.ref)
        result.update(_get_python_requires(py_require.conanfile))

    py_requires = getattr(conanfile, "py_requires", None)
    if py_requires is not None:
        for py_require in py_requires._pyrequires.values():
            result.add(py_require.ref)

    return result


def print_graph(deps_graph, out):
    requires = OrderedDict()
    build_requires = OrderedDict()
    python_requires = set()
    for node in sorted(deps_graph.nodes):
        python_requires.update(_get_python_requires(node.conanfile))
        if node.recipe in (RECIPE_CONSUMER, RECIPE_VIRTUAL):
            continue
        pref = PackageReference(node.ref, node.package_id)
        if node.build_require:
            build_requires.setdefault(pref, []).append(node)
        else:
            requires.setdefault(pref, []).append(node)

    out.writeln("Requirements", Color.BRIGHT_YELLOW)

    def _recipes(nodes):
        for _, list_nodes in nodes.items():
            node = list_nodes[0]  # For printing recipes, we can use the first one
            if node.recipe == RECIPE_EDITABLE:
                from_text = "from user folder"
            else:
                from_text = ("from local cache" if not node.remote
                             else "from '%s'" % node.remote.name)
            out.writeln("    %s %s - %s" % (str(node.ref), from_text, node.recipe),
                        Color.BRIGHT_CYAN)

    _recipes(requires)
    if python_requires:
        out.writeln("Python requires", Color.BRIGHT_YELLOW)
        for p in python_requires:
            out.writeln("    %s" % repr(p.copy_clear_rev()), Color.BRIGHT_CYAN)
    out.writeln("Packages", Color.BRIGHT_YELLOW)

    def _packages(nodes):
        for package_id, list_nodes in nodes.items():
            # The only way to have more than 1 states is to have 2
            # and one is BINARY_SKIP (privates)
            binary = set(n.binary for n in list_nodes)
            if len(binary) > 1:
                binary.remove(BINARY_SKIP)
            assert len(binary) == 1
            binary = binary.pop()
            out.writeln("    %s - %s" % (str(package_id), binary), Color.BRIGHT_CYAN)
    _packages(requires)

    if build_requires:
        out.writeln("Build requirements", Color.BRIGHT_YELLOW)
        _recipes(build_requires)
        out.writeln("Build requirements packages", Color.BRIGHT_YELLOW)
        _packages(build_requires)

    out.writeln("")
