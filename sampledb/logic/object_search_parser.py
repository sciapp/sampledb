# coding: utf-8
"""

"""
import datetime
import typing

from . import datatypes


class Literal:
    def __init__(self, input_text: str, start_position: int, value: typing.Any) -> None:
        self.input_text = input_text
        self.start_position = start_position
        self.value = value
        self.end_position = self.start_position + len(self.input_text)

    def __repr__(self) -> str:
        return '<Literal({})>'.format(self.input_text)


class Text(Literal):
    def __init__(self, input_text: str, start_position: int, value: datatypes.Text) -> None:
        super(Text, self).__init__(input_text, start_position, value)

    def __repr__(self) -> str:
        return '<Text({})>'.format(self.value.text)


class Tag(Literal):
    def __init__(self, input_text: str, start_position: int, value: str) -> None:
        super(Tag, self).__init__(input_text, start_position, value)

    def __repr__(self) -> str:
        return '<Tag(#{})>'.format(self.value)


class Boolean(Literal):
    def __init__(self, input_text: str, start_position: int, value: datatypes.Boolean) -> None:
        super(Boolean, self).__init__(input_text, start_position, value)

    def __repr__(self) -> str:
        return '<Boolean({})>'.format(self.value.value)


class Attribute(Literal):
    def __init__(self, input_text: str, start_position: int, value: typing.List[str]) -> None:
        super(Attribute, self).__init__(input_text, start_position, value)

    def __repr__(self) -> str:
        return '<Attribute({})>'.format(self.value)


class Quantity(Literal):
    def __init__(self, input_text: str, start_position: int, value: datatypes.Quantity) -> None:
        super(Quantity, self).__init__(input_text, start_position, value)

    def __repr__(self) -> str:
        return '<Quantity({})>'.format(self.value)


class Date(Literal):
    def __init__(self, input_text: str, start_position: int, value: datatypes.DateTime) -> None:
        super(Date, self).__init__(input_text, start_position, value)

    def __repr__(self) -> str:
        return '<Date({})>'.format(self.value.utc_datetime)


class Token:
    def __init__(self, input_text: str, start_position: int) -> None:
        self.input_text = input_text
        self.start_position = start_position

    def __repr__(self) -> str:
        return '<Token("{}")>'.format(self.input_text)


class Operator:
    def __init__(self, input_text: str, start_position: int, operator: str) -> None:
        self.input_text = input_text
        self.start_position = start_position
        self.operator = operator

    def __repr__(self) -> str:
        return '<Operator(operator="{}")>'.format(self.operator)


class ParseError(Exception):
    def __init__(self, message: str, start: int, end: int) -> None:
        super(ParseError, self).__init__(message)
        self.message = message
        self.start = start
        self.end = end


def split_by_texts(tokens: typing.List[typing.Union[Token]]) -> typing.List[typing.Union[Token, Text]]:
    previous_tokens = tokens
    tokens = []
    for token in previous_tokens:
        is_in_text = False
        current_token_start_position = 0
        current_token_text = ""
        for i, c in enumerate(token.input_text):
            if not is_in_text:
                if c == '"':
                    is_in_text = True
                    if current_token_text:
                        tokens.append(Token(current_token_text, current_token_start_position))
                    current_token_text = ''
                    current_token_start_position = i
                    current_token_text += c
                else:
                    current_token_text += c
            elif is_in_text:
                if c == '"':
                    is_in_text = False
                    current_token_text += c
                    tokens.append(Text(current_token_text, current_token_start_position, datatypes.Text(current_token_text[1:-1])))
                    current_token_text = ''
                    current_token_start_position = i + 1
                else:
                    current_token_text += c
        if is_in_text:
            raise ParseError("Unfinished text", current_token_start_position, len(token.input_text))
        if current_token_text:
            tokens.append(Token(current_token_text, current_token_start_position))
    return tokens


def split_by_operators(tokens: typing.List[typing.Union[Token, Text]], operators: typing.List[str]) -> typing.List[typing.Union[Token, Text, Operator]]:
    for operator in operators:
        previous_tokens = tokens
        tokens = []
        found_operator = True
        while found_operator:
            found_operator = False
            for token in previous_tokens:
                if found_operator or not isinstance(token, Token):
                    tokens.append(token)
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
                    tokens.append(Token(token.input_text, start_position))
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
                        tokens.append(Token(before_operator, start_position))
                    start_position += len(before_operator)

                    tokens.append(Operator(operator_text, start_position, operator_text))
                    start_position += len(operator_text)

                    if after_operator.strip():
                        tokens.append(Token(after_operator, start_position))
                    continue
            previous_tokens = tokens
            tokens = []
        tokens = previous_tokens
    return tokens


def apply_parentheses(tokens: typing.List[typing.Union[Token, Text, Operator]]) -> typing.List[typing.Union[Token, Text, Operator, list]]:
    previous_tokens = tokens
    tokens = []
    tokens_stack = [tokens]
    unopened_parentheses_stack = []
    for i, token in enumerate(previous_tokens):
        if not isinstance(token, Operator):
            tokens.append(token)
            continue
        if token.operator not in '()':
            tokens.append(token)
            continue
        if token.operator == '(':
            tokens.append([])
            tokens_stack.append(tokens)
            tokens = tokens[-1]
            unopened_parentheses_stack.append(i)
            # tokens.append(token)
            continue
        if token.operator == ')':
            if len(tokens_stack) < 2:
                raise ParseError("Unmatched closing parenthesis", token.start_position, token.start_position + len(token.input_text))
            # tokens.append(token)
            tokens_stack.pop()
            tokens = tokens_stack[-1]
            unopened_parentheses_stack.pop()
            continue
    if unopened_parentheses_stack:
        raise ParseError("Unmatched opening parenthesis", unopened_parentheses_stack[0], unopened_parentheses_stack[0] + 1)
    return tokens


def apply_binary_operator(tokens: typing.List[typing.Union[Token, Text, Operator, list]], operator: str):
    previous_tokens = tokens
    tokens = []
    skip_next_token = False
    for i, token in enumerate(previous_tokens):
        if skip_next_token:
            skip_next_token = False
            continue
        if isinstance(token, list):
            tokens.append(apply_binary_operator(token, operator))
            continue
        if not isinstance(token, Operator):
            tokens.append(token)
            continue
        if token.operator != operator:
            tokens.append(token)
            continue
        if token.operator == operator:
            if not tokens:
                raise ParseError("Binary operator without left operand", token.start_position, token.start_position + len(token.input_text))
            left_operand = tokens[-1]
            if not any(isinstance(left_operand, t) for t in (Token, list, Literal)):
                raise ParseError("Invalid left operand", left_operand.start_position, token.start_position + len(token.input_text))
            tokens.pop()
            if not previous_tokens[i + 1:]:
                raise ParseError("Binary operator without right operand", token.start_position, token.start_position + len(token.input_text))
            right_operand = previous_tokens[i + 1]
            if not any(isinstance(right_operand, t) for t in (Token, list, Literal)):
                raise ParseError("Invalid right operand", token.start_position, right_operand.start_position + len(right_operand.input_text))
            skip_next_token = True
            expression = [left_operand, token, right_operand]
            tokens.append(expression)
    return tokens


def apply_unary_operator(tokens: typing.List[typing.Union[Token, Text, Operator, list]], operator: str) -> typing.List[typing.Union[Token, Text, Operator, list]]:
    previous_tokens = tokens
    tokens = []
    for i, token in reversed(list(enumerate(previous_tokens))):
        if isinstance(token, list):
            tokens.insert(0, apply_unary_operator(token, operator))
            continue
        if not isinstance(token, Operator):
            tokens.insert(0, token)
            continue
        if token.operator != operator:
            tokens.insert(0, token)
            continue
        if token.operator == operator:
            if not tokens:
                raise ParseError("Unary operator without operand", token.start_position, token.start_position + len(token.input_text))
            right_operand = tokens[0]
            if not any(isinstance(right_operand, t) for t in (Token, list, Literal)):
                raise ParseError("Invalid right operand", token.start_position, right_operand.start_position + len(right_operand.input_text))
            expression = [token, right_operand]
            tokens[0] = expression
    return tokens


def remove_redundant_lists(tokens: typing.List[typing.Union[Token, Text, Operator, list]]) -> typing.List[typing.Union[Token, Text, Operator, list]]:
    if len(tokens) == 1:
        if isinstance(tokens[0], list):
            return remove_redundant_lists(tokens[0])
        return tokens[0]
    previous_tokens = tokens
    tokens = []
    for token in previous_tokens:
        if isinstance(token, list):
            tokens.append(remove_redundant_lists(token))
            continue
        tokens.append(token)
    return tokens


def parse_date(text: str) -> typing.Optional[datatypes.DateTime]:
    for datetime_format in ['%Y-%m-%d', '%m/%d/%Y', '%d.%m.%Y']:
        try:
            return datatypes.DateTime(datetime.datetime.strptime(text.strip(), datetime_format))
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

    if len_magnitude > 0:
        try:
            magnitude = int(text[:len_magnitude])
        except ValueError:
            magnitude = float(text[:len_magnitude])
        if is_negative:
            magnitude = -magnitude
        units = text[len_magnitude:]
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


def parse_attribute(text: str, start: int, end: int) -> typing.Optional[typing.List[str]]:
    if text.strip()[:1] not in 'abcdefghijklmnopqrstuvwxyz':
        return None
    attributes = text.lower().strip().split('.')
    for attribute in attributes:
        if not all(character in 'abcdefghijklmnopqrstuvwxyz0123456789_?' for character in attribute):
            raise ParseError("Invalid attribute name", start, end)
        if '?' in attribute and attribute != '?':
            raise ParseError("Invalid array placeholder", start, end)
    if attributes.count('?') > 1:
        raise ParseError("Multiple array placeholders", start, end)
    return attributes


def convert_literals(tokens: typing.List[typing.Union[Token, Text, Operator, list]]) -> typing.List[typing.Union[Operator, Literal, list]]:
    previous_tokens = tokens
    tokens = []
    for token in previous_tokens:
        start = token.start_position
        end = token.start_position + len(token.input_text)
        if not isinstance(token, Token):
            tokens.append(token)
            continue
        tag = parse_tag(token.input_text)
        if tag is not None:
            accepted_characters = 'abcdefghijklmnopqrstuvwxyz0123456789_-äöüß'
            if not tag or not all(c in accepted_characters for c in tag):
                raise ParseError("Invalid tag", start + 1, end)
            tokens.append(Tag(token.input_text, token.start_position, tag))
            continue
        boolean = parse_bool(token.input_text)
        if boolean is not None:
            tokens.append(Boolean(token.input_text, token.start_position, boolean))
            continue
        date = parse_date(token.input_text)
        if date is not None:
            tokens.append(Date(token.input_text, token.start_position, date))
            continue
        quantity = parse_quantity(token.input_text, start, end)
        if quantity is not None:
            tokens.append(Quantity(token.input_text, token.start_position, quantity))
            continue
        attributes = parse_attribute(token.input_text, start, end)
        if attributes is not None:
            tokens.append(Attribute(token.input_text, token.start_position, attributes))
            continue
        raise ParseError("Unable to parse literal", start, end)
    return tokens


def parse_query_string(text: str) -> typing.List[typing.Union[Operator, Literal, list]]:
    tokens = [Token(text, 0)]
    tokens = split_by_texts(tokens)
    tokens = split_by_operators(tokens, ['(', ')', ' in ', '==', '!=', '<=', '>=', '=', '<', '>', ' after ', ' on ', ' before ', '!', ' not ', ' and ', ' or ', ' && ', ' || '])
    tokens = convert_literals(tokens)
    tokens = apply_parentheses(tokens)
    for operator in ['in', '==', '!=', '>=', '<=', '>', '<', 'after', 'on', 'before']:
        tokens = apply_binary_operator(tokens, operator)
    for operator in ['not', '!']:
        tokens = apply_unary_operator(tokens, operator)
    for operator in ['and', '&&', 'or', '||']:
        tokens = apply_binary_operator(tokens, operator)
    tokens = remove_redundant_lists(tokens)
    return tokens
