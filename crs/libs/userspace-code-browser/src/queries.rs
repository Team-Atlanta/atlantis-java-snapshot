// https://github.com/tree-sitter/tree-sitter-c/blob/master/queries/tags.scm
pub const QUERY_C_FUNCTION_DEFINITION: &str = "(function_definition) @definition";
pub const QUERY_C_FUNCTION_REFERENCES: &str = "(call_expression function: (identifier) @name)";
pub const QUERY_C_STRUCT_DEFINITION: &str = "(struct_specifier name: (type_identifier) @name body:(_)) @definition";
pub const QUERY_C_UNION_DEFINITION: &str = "(union_specifier name: (type_identifier) @name body:(_)) @definition";
pub const QUERY_C_ENUM_DEFINITION: &str = "(enum_specifier name: (type_identifier) @name body:(_)) @definition";
pub const QUERY_C_TYPEDEF_DEFINITION: &str = "(type_definition declarator: (type_identifier) @name) @definition";
pub const QUERY_C_PREPROC_FUNCTION_DEFINITION: &str = "(preproc_function_def name: (identifier) @name value: (preproc_arg) @value) @definition";

pub const ALL_C_QUERIES: [&str; 6] = [
    QUERY_C_FUNCTION_DEFINITION,
    QUERY_C_STRUCT_DEFINITION,
    QUERY_C_ENUM_DEFINITION,
    QUERY_C_UNION_DEFINITION,
    QUERY_C_TYPEDEF_DEFINITION,
    QUERY_C_PREPROC_FUNCTION_DEFINITION,
];

