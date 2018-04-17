from typing import List, Tuple, Optional


OPERATORLIST = {"<": 2, "<=": 2, ">": 2, ">=": 2, "==": 2, "&&": 1,
                "||": 0}


class Node:
    def __init__(self, operator: str, stringleft:
                 Optional[str], stringright: Optional[str]) -> None:
        """constructor creates tree with operator
        to create left and right tree the strings which are
        left and right from the operator"""
        self.operator = operator
        if stringleft is None:
            self.left = None
        elif stringleft is not None:
            self.left = parsing_in_tree(stringleft)
        else:
            self.left = None
        if stringright is None:
            self.right = None
        elif stringright is not None:
            self.right = parsing_in_tree(stringright)
        else:
            self.right = None


def replace(string: str) -> str:
    """deletes Spaces and converts Operators"""
    string = string.replace(" and ", "&&")
    string = string.replace(" or ", "||")
    string = string.replace(" ", "")
    return string


def search_for_wrong_brackets(input: str) -> bool:
    """returns Ture if Expressions parentheses is correct"""
    if input == "":
        return False
    counter = 0
    for i in range(len(input)):
        if input[i] == "(":
            counter += 1
        if input[i] == ")":
            counter -= 1
            if counter < 0:
                return False
    if counter != 0:
        return False
    return True


def remove_unnecessary_brackets(string: str) -> str:
    """removes Outer brackets recursively"""
    while ("(" in string and
           search_for_wrong_brackets(string[1:len(string)-1]) is True):
        string = string[1:len(string)-1]
    return string


def search_operator(string: str) -> Optional[Tuple[str, int]]:
    """returns tuple with:
    ("Operator with lowest priority as String","his position")"""
    lomgest_operator = 2  # length of the longest operator
    string = remove_unnecessary_brackets(string)
    found_operators = []  # List ("operator as String","position")
    bracketcounter = 0
    for i in range(0, len(string)):
        if string[i] == "(":
            bracketcounter += 1
        if string[i] == ")":
            bracketcounter -= 1
        if bracketcounter == 0:
            for j in range(0, lomgest_operator):
                if (string[i:i+1+j] in OPERATORLIST and
                        (string[i:i+2+j] not in OPERATORLIST)):
                    found_operators.append((string[i:i+1+j], i))
                    i += j+1  # dont find < when operator is <=
    found_operators = sorting_list_by_priority(found_operators)
    if len(found_operators) is not 0:
        return found_operators[0]
    else:
        return None


def parsing_in_tree(string: str) -> Node:
    """recursive
    creates tree calls the constructor of class Node
     abort condition if no operator in string anymore"""
    string = remove_unnecessary_brackets(string)
    pos_and_op = search_operator(string)
    if pos_and_op is None:
        baum = Node(string, None, None)
    else:
        ope = pos_and_op[0]
        left = string[0:pos_and_op[1]]
        right = string[pos_and_op[1]+len(pos_and_op[0]):]
        baum = Node(ope, left, right)
    return baum


def sorting_list_by_priority(found_operators: List) -> List:
    """search operator in string with lowest priority,
    which is furthest forward"""
    found_operators.sort(key=lambda operator: OPERATORLIST[operator[0]],
                         reverse=False)
    return found_operators
