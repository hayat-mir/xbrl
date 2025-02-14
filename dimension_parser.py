# Compatibility Patch for collections.abc in Python 3.10+
import collections
if not hasattr(collections, "MutableSet"):
    from collections.abc import MutableSet
    collections.MutableSet = MutableSet

if not hasattr(collections, "MutableMapping"):
    from collections.abc import MutableMapping
    collections.MutableMapping = MutableMapping

from collections import defaultdict, OrderedDict
from arelle import XbrlConst

def process_dimension_relationships(arcrole, model_xbrl, elr):
    """
    Processes dimension relationships and constructs a hierarchical structure.
    
    :param arcrole: The arcrole (e.g., dimension-domain, domain-member)
    :param model_xbrl: The XBRL model.
    :param elr: Extended Link Role (ELR) for grouping relationships.
    :return: A dictionary representing the full dimension hierarchy.
    """
    print(f"\n🔍 Processing {arcrole} in ELR: {elr}")

    hierarchy = OrderedDict()
    parent_child_map = defaultdict(lambda: {"abstract": False, "children": OrderedDict(), "parent": None})

    relationship_set = model_xbrl.relationshipSet(arcrole, elr)
    
    if not relationship_set or not relationship_set.modelRelationships:
        print(f"⚠️ No relationships found for {arcrole} in ELR: {elr}.")
        return {}

    print(f"📌 Found {len(relationship_set.modelRelationships)} relationships in ELR: {elr}")

    all_parents = set()
    all_children = set()

    for rel in relationship_set.modelRelationships:
        parent = rel.fromModelObject
        child = rel.toModelObject

        if parent is None or child is None:
            print(f"⚠️ Skipping invalid relationship in {elr}: Parent={parent}, Child={child}")
            continue

        try:
            parent_name = f"[{elr.split('/')[-1]}] {parent.qname.localName}" if parent.qname else f"Unnamed_{id(parent)}"
            child_name = child.qname.localName if child.qname else f"Unnamed_{id(child)}"
        except AttributeError:
            print(f"⚠️ Skipping relationship: Parent or Child is missing qname attributes.")
            continue

        print(f"🔗 Relationship Found: {parent_name} → {child_name}")

        all_parents.add(parent_name)
        all_children.add(child_name)

        if parent_name not in parent_child_map:
            parent_child_map[parent_name]["abstract"] = getattr(parent, "isAbstract", False)

        if child_name not in parent_child_map:
            parent_child_map[child_name] = {
                "abstract": getattr(child, "isAbstract", False),
                "children": OrderedDict(),
                "parent": None
            }

        parent_child_map[child_name]["parent"] = parent_name
        parent_child_map[parent_name]["children"][child_name] = parent_child_map[child_name]

    print("\n📌 Parent-Child Map Constructed:")
    for parent, data in parent_child_map.items():
        print(f"  🔺 {parent}: {len(data['children'])} children")

    root_nodes = all_parents - all_children

    if not root_nodes:
        print(f"⚠️ No root nodes found for {arcrole} in ELR: {elr}")
        return {}

    print(f"\n📌 Identified {len(root_nodes)} Root Nodes for {arcrole} in {elr}: {root_nodes}")

    def build_hierarchy(node_name, visited=None, depth=0, max_depth=100):
        if visited is None:
            visited = set()
        if node_name in visited:
            print(f"⚠️ Cycle detected! Skipping {node_name}")
            return None
        if depth > max_depth:
            print(f"⚠️ Max depth reached for {node_name}. Skipping further recursion.")
            return None

        visited.add(node_name)
        node_data = parent_child_map.get(node_name, {"abstract": False, "children": {}})
        node = {
            "name": node_name,
            "abstract": node_data["abstract"],
            "children": []
        }

        for child_name in node_data["children"]:
            child_hierarchy = build_hierarchy(child_name, visited, depth + 1, max_depth)
            if child_hierarchy:
                node["children"].append(child_hierarchy)

        visited.remove(node_name)
        return node

    for root in root_nodes:
        hierarchy[root] = build_hierarchy(root)

    print(f"\n✅ Successfully Processed {len(hierarchy)} root nodes for {arcrole} in {elr}")

    return hierarchy

def parse_dimensions(model_xbrl):
    """
    Parses dimension relationships in the XBRL taxonomy and organizes them hierarchically.

    :param model_xbrl: The loaded XBRL model.
    :return: A dictionary representing the full dimension relationships.
    """
    print("\n📂 Starting Dimension Processing...")

    dim_arcroles = [
        XbrlConst.hypercubeDimension,
        XbrlConst.dimensionDomain,
        XbrlConst.domainMember
    ]

    dimensions = OrderedDict()
    for arcrole in dim_arcroles:
        relationship_set = model_xbrl.relationshipSet(arcrole)
        if not relationship_set or not relationship_set.modelRelationships:
            print(f"⚠️ No relationships found for {arcrole}. Skipping.")
            continue

        all_elrs = relationship_set.linkRoleUris
        print(f"\n🛠 Found {len(all_elrs)} ELRs for {arcrole}")

        for elr in all_elrs:
            print(f"\n🔄 Processing ELR: {elr}")
            arcrole_hierarchy = process_dimension_relationships(arcrole, model_xbrl, elr)
            dimensions.update(arcrole_hierarchy)

    print(f"\n✅ Finished Dimension Processing: {len(dimensions)} Root Nodes Extracted")

    return dimensions
