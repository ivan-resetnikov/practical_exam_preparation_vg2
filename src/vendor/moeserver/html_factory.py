"""
moeserver Copyright (c) 2026 ved Reshetnikov Ivan - alle rettigheter forbeholdt.

html_factory.py - Manipulate strings to create HTML code
"""

from collections.abc import Iterable



class HTMLElement:
    def __init__(self):
        self.parent: HTMLElement|HTMLFactory = None
        self.children: list[HTMLElement|str] = []

        self.name: str = ""

        self.attributes: dict = {}
    

    def render_html(self) -> str:
        # NOTE(vanya): Stringify the attributes
        attribute_source: str = ""

        for key, value in self.attributes.items():
            attribute_source += f" {key}=\"{value}\""

        # NOTE(vanya): Render children (Protentially recursive)
        inner_html: str = ""

        for child in self.children:
            if isinstance(child, str):
                inner_html += child
            
            if isinstance(child, HTMLElement):
                inner_html += child.render_html()

        return f"<{self.name}{attribute_source}>{inner_html}</{self.name}>"
    


class HTMLFactory:
    def __init__(self):
        self.elements: list[HTMLElement] = []
        self.root_elements: list[HTMLElement] = []
    

    def push_element(self, p_parent: HTMLElement|None, p_name: str, p_content: HTMLElement|str|None=None, **p_html_attrs) -> HTMLElement:
        e = HTMLElement()

        e.name = p_name

        # NOTE(vanya): Assign content
        if not p_content is None:
            e.children.append(p_content)

        # NOTE(vanya): Assign parent
        if isinstance(p_parent, HTMLElement):
            e.parent = p_parent
            p_parent.children.append(e)
        
        elif p_parent == None:
            e.parent = self
            self.root_elements.append(e)

        self.elements.append(e)

        # NOTE(vanya): Assign attributes
        for key, value in p_html_attrs.items():
            if key == "class_":
                e.attributes["class"] = value
            elif key == "id_":
                e.attributes["id"] = value
            else:
                e.attributes[key] = value

        return e


    def render_html(self) -> str:
        return "".join([root_element.render_html() for root_element in self.root_elements])
