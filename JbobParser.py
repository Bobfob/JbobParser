### IMPORTS

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Iterable, Iterator
import json

### CONFIG

# If true, you can use single line comments in your json file,
# but be aware that this feature can raise errors when parsing
LINE_COMMENTS: bool = False

# Maximum capacity that json can hold
MAX_CAPACITY: int = 65355

### HELPFUL

def clamp(value: Any, value_min: Any, value_max: Any) -> Any:
    return min(max(value, value_min), value_max)

type _SuppTypes = int | float | str | bool | list[int | float | str | bool] | dict[str, Any]

### TOKENS

class TokenType(Enum):
    Ident = auto()
    NumberLit = auto()
    StringLit = auto()
    BoolLit = auto()
    
    Comma = auto()
    Colon = auto()
    LBrace = auto()
    RBrace = auto()
    LBracket = auto()
    RBracket = auto()

@dataclass
class Position:
    line: int
    col: int
    
    def __str__(self) -> str: return f"({self.line}, {self.col})"
    __repr__ = __str__

@dataclass
class RangePos:
    start_pos: Position
    end_pos: Position
    
    def __str__(self) -> str: return f"({self.start_pos} -> {self.end_pos})"
    __repr__ = __str__

@dataclass
class Token:
    type: TokenType
    pos: RangePos
    value: Any | None = None
    
    def __str__(self) -> str: return f"Token({self.type}, {self.pos})" if self.value is None else f"Token({self.type}, {self.pos}, {repr(self.value)})"
    __repr__ = __str__

### ERRORS

class ScannerError(Exception): ...

class ParserError(Exception): ...

class JsonError(Exception): ...

### Scanner

class Scanner:
    def __init__(self, source: str) -> None:
        self.source = iter(source)
        self.source_lit = source
        self.index = -1
        self.line = 1
        self.col = 0
                
        self.advance()
        self.cur_pos = Position(self.line, self.col)
    
    def advance(self) -> None:
        try:
            self.cur_char = next(self.source)
            self.index += 1
            self.cur_pos = Position(self.line, self.col)
            
            if self.cur_char == '\n':
                self.line += 1
                self.col = 1
            
            else:
                self.col += 1
        
        except StopIteration:
            self.cur_pos = Position(self.line, self.col)
            
            if self.cur_char is not None:
                self.col += 1
            
            self.cur_char = None
    
    def peek(self, offset: int = 0) -> str:
        return self.source_lit[clamp(self.index + offset, 0, len(self.source_lit))]
    
    def eat(self) -> str:
        prev: str = self.peek()
        self.advance()
        return prev
    
    def expect(self, char: str | Iterable[str]) -> None:
        if not isinstance(char, str) and not isinstance(char, Iterable):
            raise TypeError("Expected 'str' or 'Iterable[str]' type")
        
        # single character
        if isinstance(char, str) and len(char) == 1:
            if self.cur_char != char:
                raise ScannerError(f'Expected \'{char}\'')
            
            self.advance()
        
        # multiple characters
        elif isinstance(char, Iterable) or len(char) > 1:
            if self.cur_char is not None and self.cur_char not in char:
                raise ScannerError(f"Expected {' | '.join(char)}")
            
            self.advance()
    
    def eat_expect(self, char: str | Iterable[str]) -> str:
        prev: str = self.peek()
        self.expect(char)
        return prev
    
    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        
        while self.cur_char is not None:
            if not LINE_COMMENTS and self.cur_char == '/' and self.peek(1) == '/':
                raise ScannerError(f"Unexpected comment at {self.cur_pos}")
            
            elif LINE_COMMENTS and self.cur_char == '/' and self.peek(1) == '/':
                while self.cur_char is not None and self.cur_char != '\n':
                    self.advance()
                
                self.advance()
                self.line += 1
                self.col = 1
            
            elif self.cur_char.isspace():
                while self.cur_char is not None and self.cur_char.isspace():
                    self.advance()
            
            elif self.cur_char.isdigit() or (self.cur_char == '.' and self.peek(1).isdigit()):
                start_pos: Position = self.cur_pos
                number: str = ''
                points: int = 0
                
                if self.cur_char == '.' and self.peek(1).isdigit():
                    points += 1
                    number += self.eat()
                
                while self.cur_char is not None and (self.cur_char.isdigit() or self.cur_char == '.'):
                    if points > 1:
                        raise ScannerError(f'Invalid amount of points in float number at {self.cur_pos}')
                    
                    number += self.eat()
                
                    if self.cur_char == '.':
                        points += 1
                        number += self.eat()
                
                tokens.append(Token(TokenType.NumberLit, RangePos(start_pos, self.cur_pos), int(number) if points == 0 else float(number)))
            
            elif self.cur_char == '"':
                start_pos: Position = self.cur_pos
                self.advance()
                string: str = ''
                
                while self.cur_char is not None and self.cur_char != '"':
                    if self.cur_char == '\\':
                        self.advance()
                        is_unicode: bool = False
                        
                        match self.cur_char:
                            case '\\': string += '\\'
                            case 'n': string += '\n'
                            case 't': string += '\t'
                            case 'b': string += '\b'
                            case 'f': string += '\f'
                            case 'r': string += '\r'
                            case 'u':
                                is_unicode = True
                                symbol_addr: str = '0x'
                                digits: list[str] = list('0123456789abcdefABCDEF')
                                self.advance()
                                
                                while self.cur_char != None and self.cur_char in digits:
                                    symbol_addr += self.eat_expect(digits)
                                    
                                    if len(symbol_addr) != 6 and self.peek() not in digits:
                                        raise ScannerError(f"Unexpected character at {Position(self.line, self.col + 1)}")
                                
                                if len(symbol_addr) > 6:
                                    raise ScannerError(f'Expected exact 4 hexadecimal digits, but got {len(symbol_addr) - 2} at {self.cur_pos}')
                                
                                string += chr(int(symbol_addr, 16))
                            case None: raise ScannerError(f"Expected escape character at {self.cur_pos}")
                            case _: raise ScannerError(f"Unexpected escape character '\\{self.cur_char}' at {self.cur_pos}")
                        
                        if not is_unicode:
                            self.advance()
                    
                    string += self.eat()
                    
                    if self.cur_char is None or self.cur_char == '\n':
                        raise ScannerError(f"Expected \"")
                
                self.advance()
                tokens.append(Token(TokenType.StringLit, RangePos(start_pos, self.cur_pos), string))
            
            elif self.cur_char.isalnum():
                start_pos: Position = self.cur_pos
                ident: str = ''
                
                while self.cur_char is not None and self.cur_char.isalnum():
                    ident += self.eat()
                
                if ident in ('false', 'true'):
                    tokens.append(Token(TokenType.BoolLit, RangePos(start_pos, self.cur_pos), False if ident == 'false' else True))
                
                else:
                    raise ScannerError(f"Expected 'false' or 'true', but got '{ident}' at {start_pos}")
            
            else:
                match self.cur_char:
                    case ':':
                        start_pos: Position = self.cur_pos
                        self.advance()
                        tokens.append(Token(TokenType.Colon, RangePos(start_pos, self.cur_pos), ':'))
                    
                    case ',':
                        start_pos: Position = self.cur_pos
                        self.advance()
                        tokens.append(Token(TokenType.Comma, RangePos(start_pos, self.cur_pos), ','))
                    
                    case '[':
                        start_pos: Position = self.cur_pos
                        self.advance()
                        tokens.append(Token(TokenType.LBracket, RangePos(start_pos, self.cur_pos), '['))
                    
                    case ']':
                        start_pos: Position = self.cur_pos
                        self.advance()
                        tokens.append(Token(TokenType.RBracket, RangePos(start_pos, self.cur_pos), ']'))
                    
                    case '{':
                        start_pos: Position = self.cur_pos
                        self.advance()
                        tokens.append(Token(TokenType.LBrace, RangePos(start_pos, self.cur_pos), '{'))
                    
                    case '}':
                        start_pos: Position = self.cur_pos
                        self.advance()
                        tokens.append(Token(TokenType.RBrace, RangePos(start_pos, self.cur_pos), '}'))
                    
                    case _:
                        raise ScannerError(f"Unexpected character '{self.cur_char}' at {self.cur_pos}")
        
        return tokens

### NODES

type JsonItems[K, V] = list[tuple[K, V]]

class NodeBase: ...

# { ... }
@dataclass
class JsonBlock(NodeBase):
    nodes: list['Node']
    
    def __find_key(self, key: str) -> int:
        index: int = 0
        
        for node in self.nodes:
            if node.key.value == key: # type: ignore
                return index
            
            index += 1
        
        raise JsonError(f'Unable to find key "{key}"')
    
    def __convert_list_to_arr(self, values: list) -> NodeBase:
        result: list[NodeBase] = []
        
        for value in values:
            if isinstance(value, (int, float)):
                result.append(NumberNode(value))
            
            elif isinstance(value, str):
                result.append(StringNode(value))
            
            elif isinstance(value, bool):
                result.append(BooleanNode(value))
            
            elif isinstance(value, dict):
                result.append(Parser(Scanner(json.dumps(value)).tokenize()).parse())
            
            elif isinstance(value, list):
                result.append(self.__convert_list_to_arr(value))
            
            else:
                raise TypeError(f"Unexpected type of value '{type(value).__name__}'")
        
        return ArrayNode(result)
    
    def items[K, V](self) -> JsonItems[K, V]:
        return [(n.key.value, n.value.value if not isinstance(n.value, JsonBlock) else n.value) for n in self.nodes] # type: ignore
    
    def keys(self) -> list[str]:
        return [n.key.value for n in self.nodes] # type: ignore
    
    def values(self) -> list[NodeBase]:
        return [n.value.value if not isinstance(n.value, JsonBlock) else n.value for n in self.nodes] # type: ignore
    
    def __str__(self) -> str: return f"\x7B{', '.join(map(str, self.nodes))}\x7D"
    __repr__ = __str__
    
    def __iter__(self) -> Iterator[NodeBase]:
        return iter(self.nodes)
    
    def __len__(self) -> int:
        return len(self.nodes)
    
    def __getitem__(self, key: str) -> _SuppTypes:
        return self.nodes[self.__find_key(key)].value # type: ignore
    
    def __setitem__(self, key: str, value: _SuppTypes) -> None:
        key_index = self.__find_key(key)
        
        if isinstance(value, (int, float)):
            self.nodes[key_index] = Node(StringNode(key), NumberNode(value))
        
        elif isinstance(value, str):
            self.nodes[key_index] = Node(StringNode(key), StringNode(value))
        
        elif isinstance(value, bool):
            self.nodes[key_index] = Node(StringNode(key), BooleanNode(value))
        
        elif isinstance(value, list):
            self.nodes[key_index] = Node(StringNode(key), self.__convert_list_to_arr(value))
        
        elif isinstance(value, dict):
            self.nodes[key_index] = Node(StringNode(key), Parser(Scanner(json.dumps(value)).tokenize()).parse())
        
        else:
            raise TypeError(f"Unexpected type of value '{type(value).__name__}'")
    
    def get_keys(self) -> list[str]:
        return [node.key.value for node in self.nodes] # type: ignore
    
    def get_values(self) -> list[NodeBase]:
        return [node.value.value for node in self.nodes] # type: ignore

# LITERAL ':' LITERAL ','?
@dataclass
class Node(NodeBase):
    key: NodeBase
    value: NodeBase
    
    def __str__(self) -> str: return f"{repr(self.key)}: {repr(self.value)}"
    __repr__ = __str__

# "..."
@dataclass
class StringNode(NodeBase):
    value: str
    
    def __str__(self) -> str: return f"\"{self.value}\""
    __repr__ = __str__

# 1, 2.2, 3., .4
@dataclass
class NumberNode(NodeBase):
    value: int | float
    
    def __str__(self) -> str: return f"{self.value}"
    __repr__ = __str__
    
    def __int__(self) -> int:
        if isinstance(self.value, int):
            return self.value
        
        return int(self.value)
    
    def __float__(self) -> float:
        if isinstance(self.value, float):
            return self.value
        
        return float(self.value)

# false or true
@dataclass
class BooleanNode(NodeBase):
    value: bool
    
    def __str__(self) -> str: return 'false' if self.value else 'true'
    __repr__ = __str__
    
    def __bool__(self) -> bool:
        return self.value
    
    def __int__(self) -> int:
        return int(self.value)

# [(LITERAL ',')*]
@dataclass
class ArrayNode(NodeBase):
    value: list[NodeBase]
    
    def __str__(self) -> str: return f"[{', '.join(map(repr, self.value))}]"
    __repr__ = __str__
    
    def __getitem__(self, index: int) -> NodeBase:
        return self.value[index]

### PARSER

class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = iter(tokens)
        self.tokens_lit = tokens
        self.index = -1
        self.fields_count = 0
        
        self.advance()
    
    def advance(self) -> None:
        try:
            self.cur_token = next(self.tokens)
            self.index += 1
        
        except StopIteration:
            self.cur_token = None
    
    def peek(self, offset: int = 0) -> Token:
        return self.tokens_lit[clamp(self.index + offset, 0, len(self.tokens_lit))]
    
    def expect(self, tok_type: TokenType, explanation: str = '', do_advance: bool = True) -> None:
        if self.cur_token == None or self.cur_token.type != tok_type:
            raise ParserError(f"Expected '{explanation}', but got '{type(self.cur_token.value).__name__}' at {self.cur_token.pos}" if self.cur_token is not None else
                              f"Expected '{explanation}'")
        
        if do_advance:
            self.advance()
    
    def eat_expect(self, tok_type: TokenType, explanation: str = '') -> Token:
        prev = self.peek()
        self.expect(tok_type, explanation)
        return prev
    
    def parse(self) -> JsonBlock:
        if self.cur_token == None:
            raise ParserError("Expected token")
        
        if self.cur_token.type == TokenType.LBrace:
            self.advance()
            fields = self.parse_fields()
            self.expect(TokenType.RBrace, '}')
            
            return JsonBlock(fields)
        
        raise ParserError(f"Unexpected token '{self.cur_token.value}' at {self.cur_token.pos}")
    
    def parse_fields(self) -> list[Node]:
        fields: list[Node] = []
        keys: list[str] = []
        
        while self.cur_token is not None and self.cur_token.type != TokenType.RBrace:
            field, pos = self.parse_field()
            self.fields_count += 1
            
            keys.append(field.key.value) # type: ignore
            
            if len(keys) != len(set(keys)):
                raise ParserError(f"Duplicated key found at {pos.start_pos}")
            
            fields.append(field)
            
            if self.fields_count > MAX_CAPACITY:
                raise ParserError("Fields count greeter then maximum capacity")

            if self.cur_token is not None and self.cur_token.type != TokenType.RBrace:
                self.expect(TokenType.Comma, ',')
            
                if self.cur_token.type == TokenType.RBrace:
                    raise ParserError(f"Unexpected trailing comma at {self.cur_token.pos}")
            
            elif self.cur_token is None:
                raise ParserError("Expected '}'")
        
        return fields
    
    def parse_field(self) -> tuple[Node, RangePos]:
        self.expect(TokenType.StringLit, 'str', do_advance = False)
        key_location: RangePos = self.cur_token.pos # type: ignore
        key: NodeBase = self.parse_primary()
        
        self.expect(TokenType.Colon, ':')
        
        value: NodeBase = self.parse_primary()
        
        return Node(key, value), key_location
    
    def parse_primary(self) -> NodeBase:
        tok = self.cur_token
        
        if tok is None:
            raise ParserError(f"Expected token")
        
        match tok.type:
            # Found number literal
            case TokenType.NumberLit:
                self.advance()
                return NumberNode(tok.value) # type: ignore
            
            # Found string literal
            case TokenType.StringLit:
                self.advance()
                return StringNode(tok.value) # type: ignore
            
            case TokenType.BoolLit:
                self.advance()
                return BooleanNode(tok.value) # type: ignore
            
            case TokenType.LBracket:
                self.advance()
                arr_values: list[NodeBase] = self.parse_arr_values()
                self.expect(TokenType.RBracket, ']')
                
                return ArrayNode(arr_values)
            
            # Found another object
            case TokenType.LBrace:
                return self.parse()
            
            case _:
                raise ParserError(f"Unexpected token '{tok.value}' at {tok.pos}")
    
    def parse_arr_values(self) -> list[NodeBase]:
        fields: list[NodeBase] = []
        
        while self.cur_token is not None and self.cur_token.type != TokenType.RBracket:
            fields.append(self.parse_primary())

            if self.cur_token.type != TokenType.RBracket:
                self.expect(TokenType.Comma, ',')
                
                if self.cur_token.type == TokenType.RBracket:
                    raise ParserError(f"Unexpected trailing comma at {self.cur_token.pos}")
        
        return fields

def parse(file_path: str) -> JsonBlock:
    """Parses source and outputs parsed json"""
    with open(file_path) as f: source = f.read()
    return Parser(Scanner(source).tokenize()).parse()

def parse_string(source: str) -> JsonBlock:
    """Parses source string into json"""
    return Parser(Scanner(source).tokenize()).parse()

def dump(tree: JsonBlock, /, indent: int = 4) -> str:
    """Converts parsed json into string"""
    return json.dumps(json.loads(str(tree)), indent=indent)
