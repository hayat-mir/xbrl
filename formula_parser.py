from collections import OrderedDict
from arelle.ViewUtilFormulae import rootFormulaObjects
from arelle.ModelFormulaObject import (
    ModelVariable, ModelVariableSet, ModelVariableSetAssertion,
    ModelFormula, ModelAssertionSet, ModelPrecondition, ModelParameter, ModelMessage
)
from arelle import XbrlConst

# Function to parse formulas and structure them hierarchically
def parse_formulas(model_xbrl):
    """
    Extracts formulas and their relationships in a hierarchical structure.
    Returns a dictionary representing the formula hierarchy.
    """
    formula_hierarchy = OrderedDict()
    root_objects = rootFormulaObjects(model_xbrl)

    # Define the arcroles related to formula processing
    formula_arcroles = [
        XbrlConst.assertionSet,
        XbrlConst.variableSet,
        XbrlConst.variableSetFilter,
        XbrlConst.variableFilter,
    ]

    for root in root_objects:
        root_label = root.xlinkLabel or f"Unnamed_{id(root)}"
        if root_label not in formula_hierarchy:
            formula_hierarchy[root_label] = OrderedDict()

        # Recursively process each formula object
        process_formula_object(root, model_xbrl, formula_hierarchy[root_label], formula_arcroles, visited=set())

    return formula_hierarchy

# Function to recursively process formula objects and construct the hierarchy
def process_formula_object(obj, model_xbrl, hierarchy, formula_arcroles, visited, depth=0, max_depth=100):
    """
    Recursively processes formula relationships and builds a hierarchical representation.
    """
    if obj is None or not hasattr(obj, "xlinkLabel"):
        return

    # Prevent infinite recursion and excessive depth
    if depth > max_depth or obj in visited:
        return

    visited.add(obj)
    obj_name = obj.xlinkLabel or f"Unnamed_{id(obj)}"

    # Store relevant properties of the formula object
    hierarchy[obj_name] = {
        "type": obj.localName,
        "label": obj.logLabel() if hasattr(obj, "logLabel") else obj.xlinkLabel or "",
        "cover": "",
        "complement": "",
        "bindAsSequence": getattr(obj, "bindAsSequence", ""),
        "expression": getattr(obj, "viewExpression", ""),
        "value": getattr(obj, "value", ""),
        "children": OrderedDict()
    }

    # Process relationships for each formula arcrole
    for arcrole in formula_arcroles:
        relationship_set = model_xbrl.relationshipSet(arcrole)
        if not relationship_set:
            continue

        for rel in relationship_set.fromModelObject(obj):
            if not hasattr(rel, "toModelObject"):
                continue

            child = rel.toModelObject
            if child is None or not hasattr(child, "xlinkLabel"):
                continue

            child_name = child.xlinkLabel or f"Unnamed_{id(child)}"

            # Add child node to the hierarchy
            if child_name not in hierarchy[obj_name]["children"]:
                hierarchy[obj_name]["children"][child_name] = {
                    "type": child.localName,
                    "label": child.logLabel() if hasattr(child, "logLabel") else child.xlinkLabel or "",
                    "cover": "true" if rel.elementQname == XbrlConst.qnVariableFilterArc and rel.isCovered else "",
                    "complement": "true" if rel.elementQname == XbrlConst.qnVariableFilterArc and rel.isComplemented else "",
                    "bindAsSequence": getattr(child, "bindAsSequence", ""),
                    "expression": getattr(child, "viewExpression", ""),
                    "value": getattr(child, "value", ""),
                    "children": OrderedDict()
                }

            # Recursively process the child formula object
            process_formula_object(
                child,
                model_xbrl,
                hierarchy[obj_name]["children"],
                formula_arcroles,
                visited,
                depth + 1,
                max_depth
            )

    visited.remove(obj)
