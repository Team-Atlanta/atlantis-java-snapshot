use std::fs::File;
use std::io::prelude::*;
use tree_sitter::{Query, QueryCursor, Language, Tree, TreeCursor, Node, Parser};
use std::cell::OnceCell;
use std::time::Duration;
use std::str;
use tree_sitter_c;
use anyhow::{Result, bail};
use crate::queries;

pub fn try_read_file(filename: &str) -> std::io::Result<String>  {
    let mut file = File::open(filename)?;
    let mut contents = String::new();
    file.read_to_string(&mut contents)?;
    Ok(contents)
}

pub fn node_to_string(node: Node, content_bytes: &[u8]) -> String {
    node.utf8_text(content_bytes).unwrap_or_default().to_string()
}

pub fn _node_option_to_result(node: Option<Node>, content_bytes: &[u8]) -> Result<String> {
    if node.is_none() {
        bail!("could not find node");
    }
    let node_text = node.unwrap().utf8_text(content_bytes)?;
    Ok(node_text.to_string())
}

pub fn node_option_to_string(node: Option<Node>, content_bytes: &[u8]) -> String {
    if node.is_none() {
        return "".to_string();
    }
    let node = node.unwrap();
    node_to_string(node, content_bytes)
}

pub fn node_to_multiline_string(node: Node, content_bytes: &[u8]) -> String {
    let start_row = node.start_position().row;
    let end_row = node.end_position().row;
    let content_str_res = str::from_utf8(content_bytes);
    if content_str_res.is_err() {
        return "".to_string();
    }
    let content_str = content_str_res.unwrap();
    let mut ret = content_str.split('\n').skip(start_row).take(end_row - start_row + 1).collect::<Vec<&str>>().join("\n");
    ret.push_str("\n");
    ret
}



/// Use to track tree-sitter cursor visit operations
pub enum DfsOp {
    None,
    Child,
    Sibling,
}

impl DfsOp {
    pub fn undo_dfs_op(&self, cursor: &mut TreeCursor) -> bool {
        match self {
            DfsOp::Child => cursor.goto_parent(),
            _ => true,
        }
    }
}

enum DfsStage {
    Base,
    Child,
    PreSibling,
    Sibling,
    Epilogue,
}

struct DfsContext {
    stage: DfsStage,
    prev_op: DfsOp,
}

/// Traversal algorithm for tree-sitter cursor
pub struct TreeSitterTraversal<F, C: ?Sized>
where
    F: Fn(&TreeCursor, &C) -> bool,
{
    predicate: F,
    _marker: std::marker::PhantomData<C>,
}

impl<F, C: ?Sized> TreeSitterTraversal<F, C>
where 
    F: Fn(&TreeCursor, &C) -> bool,
{
    pub fn new(predicate: F) -> Self {
        Self {
            predicate,
            _marker: std::marker::PhantomData,
        }
    }

    pub fn dfs<'a>(&self, cursor: &mut TreeCursor<'a>, context: &C) -> Option<Node<'a>> {
        let mut call_stack = vec![];
        let mut ret = None;
        call_stack.push(DfsContext {stage: DfsStage::Base, prev_op: DfsOp::None});
        while call_stack.len() > 0 {
            let DfsContext {stage, prev_op} = call_stack.pop().expect("Popping from empty stack");
            match stage {
                DfsStage::Base => {
                    let result = (self.predicate)(&cursor, &context);
                    if result {
                        ret = Some(cursor.node());
                        continue;
                    }
                    // traverse child first
                    let has_next = cursor.goto_first_child();
                    if has_next {
                        // handler and snapshot prev_op
                        call_stack.push(DfsContext {stage: DfsStage::Child, prev_op});
                        // recursive call
                        call_stack.push(DfsContext {stage: DfsStage::Base, prev_op: DfsOp::Child});
                        continue;
                    }
                    // go to next stage
                    call_stack.push(DfsContext {stage: DfsStage::PreSibling, prev_op});
                }
                DfsStage::Child => {
                    if ret.is_some() {
                        continue;
                    }
                    call_stack.push(DfsContext {stage: DfsStage::PreSibling, prev_op});
                }
                DfsStage::PreSibling => {
                    // then check sibling
                    let has_next = cursor.goto_next_sibling();
                    if has_next {
                        call_stack.push(DfsContext {stage: DfsStage::Sibling, prev_op});
                        call_stack.push(DfsContext {stage: DfsStage::Base, prev_op: DfsOp::Sibling});
                        continue;
                    }
                    call_stack.push(DfsContext {stage: DfsStage::Epilogue, prev_op});
                }
                DfsStage::Sibling => {
                    if ret.is_some() {
                        continue;
                    }
                    call_stack.push(DfsContext {stage: DfsStage::Epilogue, prev_op});
                }
                DfsStage::Epilogue => {
                    prev_op.undo_dfs_op(cursor);
                    ret = None;
                }
            }
        }
        ret
    }

    
    #[allow(dead_code)]
    pub fn search_ancestors<'a>(&self, cursor: &mut TreeCursor<'a>, context: &C) -> Option<Node<'a>> {
        loop {
            let result = (self.predicate)(&cursor, &context);
            if result {
                return Some(cursor.node());
            }
            if !cursor.goto_parent() {
                break;
            }
        }
        None
    }
}


#[allow(dead_code)]
pub fn backtrack_node_sequence<'a>(cursor: &mut TreeCursor<'a>, sequence: Vec<&str>) -> Node<'a> {
    assert!(!sequence.is_empty(), "empty sequence");
    let mut idx = 0;
    let mut node = cursor.node();
    loop {
        if !cursor.goto_parent() {
            break;
        }
        idx = (idx + 1) % sequence.len();
        if cursor.node().grammar_name() != sequence[idx] {
            break;
        }
        node = cursor.node();
    }
    node
}

/// Use to preallocate read-only query related structs
#[derive(Default)]
pub struct QueryContext {
    query_c_function_references: OnceCell<Query>,
    query_c_all: OnceCell<Query>,
    query_c_all_string: String,
    c_language: OnceCell<Language>,
}

impl QueryContext {
    fn get_query<'a>(query: &'a OnceCell<Query>, language: &Language, text: &str) -> &'a Query {
        query.get_or_init(|| {
            Query::new(language, text).expect("Query didn't get created")
        })
    }

    fn ts_c_language() -> Language {
        tree_sitter_c::LANGUAGE.into()
    }

    pub fn get_c_language<'a>(&'a self) -> &'a Language {
        self.c_language.get_or_init(|| {
            Self::ts_c_language()
        })
    }

    
    /// Initialize all relevant tree-sitter constructs from string
    pub fn bootstrap_tree_sitter_walk_from_str(contents: &str) -> Result<Tree> {
        let mut parser = Parser::new();
        parser.set_language(&Self::ts_c_language()).expect("Error loading tree sitter language");
        let timeout = Duration::from_secs(5);
        parser.set_timeout_micros(timeout.as_micros() as u64);
        let tree_res = parser.parse(&contents, None);
        if tree_res.is_none() {
            bail!("Tree sitter parse failed");
        }
        Ok(tree_res.unwrap())
    }

    /// Initialize all relevant tree-sitter constructs from string
    pub fn bootstrap_tree_sitter_parse_from_str(contents: &str) -> Result<(Tree, Self, QueryCursor)> {
        let mut qc = Self::default();
        qc.query_c_all_string = queries::ALL_C_QUERIES.join("\n");
        let tree = Self::bootstrap_tree_sitter_walk_from_str(contents)?;
        let qcursor = QueryCursor::new();
        Ok((tree, qc, qcursor))
    }

    
    pub fn get_query_c_function_references(&self) -> &Query {
        Self::get_query(&self.query_c_function_references, self.get_c_language(), queries::QUERY_C_FUNCTION_REFERENCES)
    }

    pub fn get_query_c_all(&self) -> &Query {
        Self::get_query(&self.query_c_all, self.get_c_language(), &self.query_c_all_string)
    }
}
