# coding: utf-8
"""

"""
import datetime
import string
import typing

from . import datatypes


class Literal:
    def __init__(self, input_text: str, start_position: int, value: typing.Any) -> None:
        self.input_text = input_text
        self.start_position = start_position
        self.value = value
        self.end_position = self.start_position + len(self.input_text)

    def __repr__(self) -> str:
        return f'<Literal({self.input_text})>'


class Text(Literal):
    def __init__(self, input_text: str, start_position: int, value: datatypes.Text) -> None:
        super().__init__(input_text, start_position, value)

    def __repr__(self) -> str:
        return f'<Text({self.value.text})>'


class Tag(Literal):
    def __init__(self, input_text: str, start_position: int, value: str) -> None:
        super().__init__(input_text, start_position, value)

    def __repr__(self) -> str:
        return f'<Tag(#{self.value})>'


class Reference(Literal):
    def __init__(self, input_text: str, start_position: int, value: int) -> None:
        super().__init__(input_text, start_position, value)

    def __repr__(self) -> str:
        return f'<Reference(#{self.value})>'


class Boolean(Literal):
    def __init__(self, input_text: str, start_position: int, value: datatypes.Boolean) -> None:
        super().__init__(input_text, start_position, value)

    def __repr__(self) -> str:
        return f'<Boolean({self.value.value})>'


class Attribute(Literal):
    def __init__(self, input_text: str, start_position: int, value: typing.List[str], is_partial_attribute: bool) -> None:
        super().__init__(input_text, start_position, value)
        self.is_partial_attribute = is_partial_attribute

    def __repr__(self) -> str:
        return f'<Attribute({self.value}, {self.is_partial_attribute})>'


class Null(Literal):
    def __init__(self, input_text: str, start_position: int, value: str) -> None:
        super().__init__(input_text, start_position, value)

    def __repr__(self) -> str:
        return f'<Null({self.value})>'


class Quantity(Literal):
    def __init__(self, input_text: str, start_position: int, value: datatypes.Quantity) -> None:
        super().__init__(input_text, start_position, value)

    def __repr__(self) -> str:
        return f'<Quantity({self.value})>'


class Date(Literal):
    def __init__(self, input_text: str, start_position: int, value: datatypes.DateTime) -> None:
        super().__init__(input_text, start_position, value)

    def __repr__(self) -> str:
        return f'<Date({self.value.utc_datetime})>'


class Token:
    def __init__(self, input_text: str, start_position: int) -> None:
        self.input_text = input_text
        self.start_position = start_position

    def __repr__(self) -> str:
        return f'<Token("{self.input_text}")>'


class Operator:
    def __init__(self, input_text: str, start_position: int, operator: str) -> None:
        self.input_text = input_text
        self.start_position = start_position
        self.operator = operator

    def __repr__(self) -> str:
        return f'<Operator(operator="{self.operator}")>'


class ParseError(Exception):
    def __init__(self, message: str, start: int, end: int) -> None:
        super().__init__(message)
        self.message = message
        self.start = start
        self.end = end


def split_by_texts(tokens: typing.List[typing.Union[Token]]) -> typing.List[typing.Union[Token, Text]]:
    new_tokens: typing.List[typing.Union[Token, Text]] = []
    for token in tokens:
        is_in_text = False
        current_token_start_position = 0
        current_token_text = ""
        for i, c in enumerate(token.input_text):
            if not is_in_text:
                if c == '"':
                    is_in_text = True
                    if current_token_text:
                        new_tokens.append(Token(current_token_text, current_token_start_position))
                    current_token_text = ''
                    current_token_start_position = i
                    current_token_text += c
                else:
                    current_token_text += c
            elif is_in_text:
                if c == '"':
                    is_in_text = False
                    current_token_text += c
                    new_tokens.append(Text(current_token_text, current_token_start_position, datatypes.Text(current_token_text[1:-1])))
                    current_token_text = ''
                    current_token_start_position = i + 1
                else:
                    current_token_text += c
        if is_in_text:
            raise ParseError("Unfinished text", current_token_start_position, len(token.input_text))
        if current_token_text:
            new_tokens.append(Token(current_token_text, current_token_start_position))
    return new_tokens


def split_by_operators(tokens: typing.List[typing.Union[Token, Text]], operators: typing.List[str]) -> typing.List[typing.Union[Token, Text, Operator]]:
    new_tokens: typing.List[typing.Union[Token, Text, Operator]] = list(tokens)
    for operator in operators:
        previous_tokens = new_tokens
        new_tokens = []
        found_operator = True
        while found_operator:
            found_operator = False
            for token in previous_tokens:
                if found_operator or not isinstance(token, Token):
                    new_tokens.append(token)
                    continue
                start_position = token.start_position
                if ' ' + token.input_text + ' ' == operator:
                    found_operator = True
                    operator_text = operator[1:-1]
                    before_operator, after_operator = '', ''
                elif (' ' + token.input_text).startswith(operator) and not token.input_text.startswith(operator):
                    found_operator = True
                    operator_text = operator[1:]
                    before_operator, after_operator = (' ' + token.input_text).split(operator, 1)
                elif (token.input_text + ' ').endswith(operator) and not token.input_text.endswith(operator):
                    found_operator = True
                    operator_text = operator[:-1]
                    before_operator, after_operator = (token.input_text + ' ').split(operator, 1)
                elif operator in token.input_text:
                    found_operator = True
                    operator_text = operator
                    before_operator, after_operator = token.input_text.split(operator, 1)
                else:
                    new_tokens.append(Token(token.input_text, start_position))
                    continue
                if found_operator:
                    leading_whitespace = len(operator_text) - len(operator_text.lstrip())
                    if leading_whitespace:
                        before_operator = before_operator + operator_text[:leading_whitespace]
                        operator_text = operator_text[leading_whitespace:]

                    trailing_whitespace = len(operator_text) - len(operator_text.rstrip())
                    if trailing_whitespace:
                        after_operator = operator_text[len(operator_text) - trailing_whitespace:] + after_operator
                        operator_text = operator_text[:len(operator_text) - trailing_whitespace]

                    if before_operator.strip():
                        new_tokens.append(Token(before_operator, start_position))
                    start_position += len(before_operator)

                    new_tokens.append(Operator(operator_text, start_position, operator_text))
                    start_position += len(operator_text)

                    if after_operator.strip():
                        new_tokens.append(Token(after_operator, start_position))
                    continue
            previous_tokens = new_tokens
            new_tokens = []
        new_tokens = previous_tokens
    return new_tokens


def apply_parentheses(tokens: typing.List[typing.Union[Text, Operator, Literal]]) -> typing.List[typing.Union[Text, Operator, Literal, typing.List[typing.Any]]]:
    previous_tokens = tokens
    new_tokens: typing.List[typing.Union[Text, Operator, Literal, typing.List[typing.Any]]] = []
    tokens_stack = [new_tokens]
    unopened_parentheses_stack = []
    for i, token in enumerate(previous_tokens):
        if not isinstance(token, Operator):
            new_tokens.append(token)
            continue
        if token.operator not in '()':
            new_tokens.append(token)
            continue
        if token.operator == '(':
            inner_new_tokens: typing.List[typing.Union[Text, Operator, Literal, typing.List[typing.Any]]] = []
            new_tokens.append(inner_new_tokens)
            tokens_stack.append(inner_new_tokens)
            new_tokens = inner_new_tokens
            unopened_parentheses_stack.append(i)
            continue
        if token.operator == ')':
            if len(tokens_stack) < 2:
                raise ParseError("Unmatched closing parenthesis", token.start_position, token.start_position + len(token.input_text))
            tokens_stack.pop()
            new_tokens = tokens_stack[-1]
            unopened_parentheses_stack.pop()
            continue
    if unopened_parentheses_stack:
        raise ParseError("Unmatched opening parenthesis", unopened_parentheses_stack[0], unopened_parentheses_stack[0] + 1)
    return new_tokens


def apply_binary_operator(
        tokens: typing.List[typing.Union[Text, Operator, Literal, typing.List[typing.Any]]],
        operator: str
) -> typing.List[typing.Union[Text, Operator, Literal, typing.List[typing.Any]]]:
    previous_tokens = [
        apply_binary_operator(token, operator) if isinstance(token, list) else token
        for token in tokens
    ]
    new_tokens: typing.List[typing.Union[Text, Operator, Literal, typing.List[typing.Any]]] = []
    skip_next_token = False
    for i, token in enumerate(previous_tokens):
        if skip_next_token:
            skip_next_token = False
            continue
        if not isinstance(token, Operator):
            new_tokens.append(token)
            continue
        if token.operator != operator:
            new_tokens.append(token)
            continue
        if token.operator == operator:
            if not new_tokens:
                raise ParseError("Binary operator without left operand", token.start_position, token.start_position + len(token.input_text))
            left_operand = new_tokens[-1]
            if not isinstance(left_operand, (Token, list, Literal)):
                raise ParseError("Invalid left operand", left_operand.start_position, token.start_position + len(token.input_text))
            new_tokens.pop()
            if not previous_tokens[i + 1:]:
                raise ParseError("Binary operator without right operand", token.start_position, token.start_position + len(token.input_text))
            right_operand = previous_tokens[i + 1]
            if not isinstance(right_operand, (Token, list, Literal)):
                raise ParseError("Invalid right operand", token.start_position, right_operand.start_position + len(right_operand.input_text))
            skip_next_token = True
            expression = [left_operand, token, right_operand]
            new_tokens.append(expression)
    return new_tokens


def apply_unary_operator(
        tokens: typing.List[typing.Union[Text, Operator, Literal, typing.List[typing.Any]]],
        operator: str
) -> typing.List[typing.Union[Text, Operator, Literal, typing.List[typing.Any]]]:
    previous_tokens = tokens
    new_tokens: typing.List[typing.Union[Text, Operator, Literal, typing.List[typing.Any]]] = []
    for token in reversed(list(previous_tokens)):
        if isinstance(token, list):
            new_tokens.insert(0, apply_unary_operator(token, operator))
            continue
        if not isinstance(token, Operator):
            new_tokens.insert(0, token)
            continue
        if token.operator != operator:
            new_tokens.insert(0, token)
            continue
        if token.operator == operator:
            if not new_tokens:
                raise ParseError("Unary operator without operand", token.start_position, token.start_position + len(token.input_text))
            right_operand = new_tokens[0]
            if not isinstance(right_operand, (Token, list, Literal)):
                raise ParseError("Invalid right operand", token.start_position, right_operand.start_position + len(right_operand.input_text))
            expression = [token, right_operand]
            new_tokens[0] = expression
    return new_tokens


def apply_partial_attributes(
        tokens: typing.List[typing.Union[Text, Operator, Literal, typing.List[typing.Any]]],
) -> typing.List[typing.Union[Text, Operator, Literal, typing.List[typing.Any]]]:
    previous_tokens = tokens
    new_tokens: typing.List[typing.Union[Text, Operator, Literal, typing.List[typing.Any]]] = []
    for token in reversed(list(previous_tokens)):
        if isinstance(token, list):
            new_tokens.insert(0, apply_partial_attributes(token))
            continue
        if isinstance(token, Attribute) and token.is_partial_attribute:
            if not new_tokens or not isinstance(new_tokens[0], list):
                raise ParseError("Partial attribute without inner clause", token.start_position, token.start_position + len(token.input_text))
            inner_clause = new_tokens[0]
            while isinstance(inner_clause, list) and len(inner_clause) == 1:
                inner_clause = inner_clause[0]
            if not isinstance(inner_clause, list):
                raise ParseError("Partial attribute with invalid inner clause", token.start_position, token.start_position + len(token.input_text))
            expression = [token, new_tokens[0]]
            new_tokens[0] = expression
        else:
            new_tokens.insert(0, token)
            continue
    return new_tokens


def remove_redundant_lists(
        tokens: typing.List[typing.Union[Text, Operator, Literal, typing.List[typing.Any]]]
) -> typing.Union[Text, Operator, Literal, typing.List[typing.Union[Text, Operator, Literal, typing.List[typing.Any]]]]:
    if len(tokens) == 1:
        if isinstance(tokens[0], list):
            return remove_redundant_lists(tokens[0])
        return tokens[0]
    previous_tokens = tokens
    new_tokens: typing.List[typing.Union[Text, Operator, Literal, typing.List[typing.Any]]] = []
    for token in previous_tokens:
        if isinstance(token, list):
            new_tokens.append(remove_redundant_lists(token))
            continue
        new_tokens.append(token)
    return new_tokens


def parse_date(text: str) -> typing.Optional[datatypes.DateTime]:
    for datetime_format in ['%Y-%m-%d', '%m/%d/%Y', '%d.%m.%Y']:
        try:
            return datatypes.DateTime(datetime.datetime.strptime(text.strip(), datetime_format).replace(tzinfo=datetime.timezone.utc))
        except ValueError:
            pass
    return None


def parse_quantity(text: str, start: int, end: int) -> typing.Optional[datatypes.Quantity]:
    had_decimal_point = False
    len_magnitude = 0
    start += text.find(text.lstrip())
    text = text.strip()
    end = start + len(text)
    is_negative = False

    for index, character in enumerate(text):
        if index == 0 and character == '-':
            is_negative = True
            continue
        if not character.isdigit():
            if not had_decimal_point and character == ".":
                had_decimal_point = True
            else:
                len_magnitude = index
                break
        else:
            len_magnitude = len(text)
    if is_negative:
        text = text[1:]
        len_magnitude -= 1
    if len_magnitude != len(text) and text[len_magnitude].lower() == 'e':
        for index, character in enumerate(text[len_magnitude + 1:]):
            len_exponent = index
            if index == 0 and character == '-':
                continue
            if not character.isdigit():
                break
        else:
            len_exponent = len(text[len_magnitude + 1:])
        if len_exponent > 0:
            len_magnitude += 1 + len_exponent

    if len_magnitude > 0:
        magnitude: typing.Union[int, float]
        try:
            magnitude = int(text[:len_magnitude])
        except ValueError:
            magnitude = float(text[:len_magnitude])
        if is_negative:
            magnitude = -magnitude
        units: typing.Optional[str] = text[len_magnitude:]
        if units:
            units = units.strip()
        if not units:
            units = None
        try:
            return datatypes.Quantity(magnitude, units)
        except ValueError:
            raise ParseError("Unable to parse units", start + len_magnitude, end)
    return None


def parse_bool(text: str) -> typing.Optional[datatypes.Boolean]:
    text = text.lower().strip()
    if text == 'true':
        return datatypes.Boolean(True)
    if text == 'false':
        return datatypes.Boolean(False)
    return None


def parse_tag(text: str) -> typing.Optional[str]:
    text = text.strip()
    if text.startswith('#'):
        return text[1:]
    return None


def parse_reference(text: str) -> typing.Optional[int]:
    text = text.strip()
    if text.startswith('#') and all(c in '0123456789' for c in text[1:]):
        try:
            value = int(text[1:])
        except ValueError:
            return None
        if str(value) == text[1:]:
            return value
    return None


def parse_null(text: str) -> typing.Optional[str]:
    if text.strip().lower() == 'null':
        return 'null'
    return None


def parse_attribute(text: str, start: int, end: int) -> typing.Tuple[typing.Optional[typing.List[str]], bool]:
    text = text.strip()
    if text[:1] not in string.ascii_letters + '*':
        return None, False
    attributes = text.split('.')
    is_partial_attribute = len(attributes) > 1 and not attributes[-1]
    if is_partial_attribute:
        attributes.pop()
    for attribute in attributes:
        # empty attributes
        if not attribute:
            raise ParseError("Invalid attribute name", start, end)
        # object reference dereferencing
        if attribute.startswith('*'):
            attribute = attribute[1:]
        # array placeholder
        if '?' in attribute:
            if attribute == '?':
                continue
            else:
                raise ParseError("Invalid array placeholder", start, end)
        # array indices
        if attribute[0] in string.digits:
            if all(character in string.digits for character in attribute):
                continue
            else:
                raise ParseError("Invalid array index", start, end)
        # attribute name
        if attribute[0] in string.ascii_letters:
            if all(character in (string.ascii_letters + string.digits + '_') for character in attribute):
                continue
            else:
                raise ParseError("Invalid attribute name", start, end)
        raise ParseError("Invalid attribute name", start, end)
    return attributes, is_partial_attribute


def convert_literals(tokens: typing.List[typing.Union[Token, Text, Operator]]) -> typing.List[typing.Union[Text, Operator, Literal]]:
    previous_tokens = tokens
    new_tokens: typing.List[typing.Union[Text, Operator, Literal]] = []
    for token in previous_tokens:
        if not isinstance(token, Token):
            new_tokens.append(token)
            continue

        start = token.start_position
        end = token.start_position + len(token.input_text)

        null = parse_null(token.input_text)
        if null is not None:
            new_tokens.append(Null(token.input_text, token.start_position, null))
            continue

        reference = parse_reference(token.input_text)
        if reference is not None:
            new_tokens.append(Reference(token.input_text, token.start_position, reference))
            continue

        tag = parse_tag(token.input_text)
        if tag is not None:
            accepted_characters = 'abcdefghijklmnopqrstuvwxyz0123456789_-äöüß'
            if not tag or not all(c in accepted_characters for c in tag):
                raise ParseError("Invalid tag", start + 1, end)
            new_tokens.append(Tag(token.input_text, token.start_position, tag))
            continue

        boolean = parse_bool(token.input_text)
        if boolean is not None:
            new_tokens.append(Boolean(token.input_text, token.start_position, boolean))
            continue

        date = parse_date(token.input_text)
        if date is not None:
            new_tokens.append(Date(token.input_text, token.start_position, date))
            continue

        quantity = parse_quantity(token.input_text, start, end)
        if quantity is not None:
            new_tokens.append(Quantity(token.input_text, token.start_position, quantity))
            continue

        attributes, is_partial_attribute = parse_attribute(token.input_text, start, end)
        if attributes is not None:
            new_tokens.append(Attribute(token.input_text, token.start_position, attributes, is_partial_attribute))
            continue

        raise ParseError("Unable to parse literal", start, end)
    return new_tokens


def parse_query_string(text: str) -> typing.Union[Text, Operator, Literal, typing.List[typing.Union[Text, Operator, Literal, typing.List[typing.Any]]]]:
    tokens1: typing.List[Token] = [Token(text, 0)]
    tokens2: typing.List[typing.Union[Token, Text]] = split_by_texts(tokens1)
    tokens3: typing.List[typing.Union[Token, Text, Operator]] = split_by_operators(tokens2, ['(', ')', ' in ', '==', '!=', '<=', '>=', '=', '<', '>', ' after ', ' on ', ' before ', '!', ' not ', ' and ', ' or ', ' && ', ' || '])
    tokens4: typing.List[typing.Union[Text, Operator, Literal]] = convert_literals(tokens3)
    tokens5: typing.List[typing.Union[Text, Operator, Literal, typing.List[typing.Any]]] = apply_parentheses(tokens4)
    tokens5 = apply_partial_attributes(tokens5)
    for operator in ['in', '==', '!=', '>=', '<=', '>', '<', 'after', 'on', 'before']:
        tokens5 = apply_binary_operator(tokens5, operator)
    for operator in ['not', '!']:
        tokens5 = apply_unary_operator(tokens5, operator)
    for operator in ['and', '&&', 'or', '||']:
        tokens5 = apply_binary_operator(tokens5, operator)
    tokens6: typing.Union[Text, Operator, Literal, typing.List[typing.Union[Text, Operator, Literal, typing.List[typing.Any]]]] = remove_redundant_lists(tokens5)
    return tokens6
