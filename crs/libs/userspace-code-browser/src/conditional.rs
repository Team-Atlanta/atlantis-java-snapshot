use tree_sitter::{TreeCursor, Tree};
use anyhow::{Result, bail};
use crate::tree_sitter_helper::{QueryContext, TreeSitterTraversal, node_to_multiline_string, backtrack_node_sequence, try_read_file};

// Walk the tree until find conditional
fn get_conditional_helper(contents: &str, tree: &Tree, linum: usize) -> Result<String> {
    let content_bytes = contents.as_bytes();
    let root_node = tree.root_node();

    // Point is zero-indexed so let's decrement
    if linum == 0 {
        bail!("linum of zero provided, must be at least one");
    }
    let linum = linum - 1;

    let mut tcursor = root_node.walk();
    let mut tcursor2 = root_node.walk();

    // Searcher for nodes with line number
    let traverse_linum = TreeSitterTraversal::new(|cursor: &TreeCursor, linum: &usize| -> bool {
        cursor.node().start_position().row == *linum
    });

    // Searcher for nodes with grammar name only
    let traverse_grammar_name = TreeSitterTraversal::new(|cursor: &TreeCursor, fields: &Vec<&str>| -> bool {
        let node = cursor.node();
        fields.iter().fold(false, |acc, &x| acc || node.grammar_name() == x)
    });

    // Searcher for nodes with both line number and grammar
    let traverse_conditional = TreeSitterTraversal::new(|cursor: &TreeCursor, (fields, linum): &(Vec<&str>, usize)| -> bool {
        let node = cursor.node();
        node.start_position().row == *linum
            && fields.iter().fold(false, |acc, &x| acc || node.grammar_name() == x)
    });

    let grammar_names = vec!["if_statement", "switch_statement"];

    // check for nodes at the exact line number provided
    let linum_node = traverse_linum.dfs(&mut tcursor, &linum);
    if linum_node.is_none() {
        bail!("no nodes found at line {}", linum + 1);
    }

    // check for conditional children
    let mut cond_node = traverse_conditional.dfs(&mut tcursor2, &(grammar_names.clone(), linum));
    // no conditionals found at line number
    let check = cond_node.is_none();
    if check {
        // maybe we're in a switch block or a multi-line if condition. check ancestors
        let parent_node = traverse_grammar_name.search_ancestors(&mut tcursor, &grammar_names.clone());
        if parent_node.is_none() {
            bail!("no conditional statement found at line {}", linum + 1);
        }
        cond_node = parent_node;
        tcursor2.reset_to(&tcursor);
    }

    let cond_node = cond_node.expect("node is none and didn't return");
    assert!(cond_node.grammar_name() == "if_statement" || cond_node.grammar_name() == "switch_statement",
        "node type is not conditional");

    // if statement could be a child to else_clause
    let check = cond_node.grammar_name() == "if_statement";
    let ret_node = if check {
        // unwrap if-else chains
        backtrack_node_sequence(&mut tcursor2, vec!["if_statement", "else_clause"])
    }
    else {
        // switch statement can just be returned as-is
        cond_node
    };

    Ok(node_to_multiline_string(ret_node, content_bytes))
}

pub fn get_conditional(path: &str, linum: usize) -> Result<String> {
    let file_contents = try_read_file(path)?;
    let tree = QueryContext::bootstrap_tree_sitter_walk_from_str(&file_contents)?;
    get_conditional_helper(&file_contents, &tree, linum)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_if_else_block() {
        let contents = r#"
            foo();
            if (cond || !(cond) && 1) {
                a = 1;
            }
            else if (cond + cond < cond) { // this is considered (else_clause (if_statement))
                a = 2;
            }
            else if (cond && cond) {
                a = 3;
            }
            else {
                a = 4;
            }
            bar();
        "#;
        let mut trimmed = contents[1..].trim_end().to_string();
        trimmed.push_str("\n");
        let contents = &trimmed;
        let line_count = contents.split('\n').count();
        let mut truth = contents.split('\n').skip(1).take(line_count - 3).collect::<Vec<_>>().join("\n");
        truth.push_str("\n");

        let tree = QueryContext::bootstrap_tree_sitter_walk_from_str(contents).unwrap();
        for linum in 2..=line_count-2 {
            let result = get_conditional_helper(contents, &tree, linum).expect(&format!("failed at line {}", linum));
            assert_eq!(result, truth, "failed at line {}", linum);
        }
        for linum in [1, line_count-1] {
            let result = get_conditional_helper(contents, &tree, linum);
            assert!(result.is_err(), "failed at line {}", linum);
        }
    }

    #[test]
    fn test_switch_case_block() {
        let contents = r#"
            foo();
            switch (cond) {
                case 1:
                    a = 3;
                    break;
                case 2: {
                    int c = 12;
                    a = 4 + c;
                    break;
                }
                default:
                    a = 10;
                    break;
            }
            bar();
        "#;
        let mut trimmed = contents[1..].trim_end().to_string();
        trimmed.push_str("\n");
        let contents = &trimmed;
        let line_count = contents.split('\n').count();
        let mut truth = contents.split('\n').skip(1).take(line_count - 3).collect::<Vec<_>>().join("\n");
        truth.push_str("\n");

        let tree = QueryContext::bootstrap_tree_sitter_walk_from_str(contents).unwrap();
        for linum in 2..=line_count-2 {
            let result = get_conditional_helper(contents, &tree, linum).expect(&format!("failed at line {}", linum));
            assert_eq!(result, truth, "failed at line {}", linum);
        }
        for linum in [1, line_count-1] {
            let result = get_conditional_helper(contents, &tree, linum);
            assert!(result.is_err(), "failed at line {}", linum);
        }
    }

    #[test]
    fn test_sibling_if_else_block() {
        let contents = r#"
            if (cond || !(cond) && 1) {
                a = 1;
            }
            else if (cond + cond < cond) { // this is considered (else_clause (if_statement))
                a = 2;
            }
            if (cond && cond) {
                a = 3;
            }
            else {
                a = 4;
            }
        "#;
        let mut trimmed = contents[1..].trim_end().to_string();
        trimmed.push_str("\n");
        let contents = &trimmed;
        let mut first_half = contents.split('\n').take(6).collect::<Vec<_>>().join("\n");
        first_half.push_str("\n");
        let second_half = contents.split('\n').skip(6).collect::<Vec<_>>().join("\n");
         
        let tree = QueryContext::bootstrap_tree_sitter_walk_from_str(contents).unwrap();
        for linum in 1..=6 {
            let result = get_conditional_helper(contents, &tree, linum).expect(&format!("failed at line {}", linum));
            assert_eq!(result, first_half, "failed at line {}", linum);
        }
        for linum in 7..=12 {
            let result = get_conditional_helper(contents, &tree, linum).expect(&format!("failed at line {}", linum));
            assert_eq!(result, second_half, "failed at line {}", linum);
        }
    }

    #[test]
    fn test_sibling_switch_case_block() {
        let contents = r#"
            switch (cond) {
                case 1:
                    a = 3;
                    break;
            }
            switch (cond) {
                case 2: {
                    int c = 12;
                    a = 4 + c;
                    break;
                }
                default:
                    a = 10;
                    break;
            }
        "#;
        let mut trimmed = contents[1..].trim_end().to_string();
        trimmed.push_str("\n");
        let contents = &trimmed;
        let mut first_half = contents.split('\n').take(5).collect::<Vec<_>>().join("\n");
        first_half.push_str("\n");
        let second_half = contents.split('\n').skip(5).collect::<Vec<_>>().join("\n");
         
        let tree = QueryContext::bootstrap_tree_sitter_walk_from_str(contents).unwrap();
        for linum in 1..=5 {
            let result = get_conditional_helper(contents, &tree, linum).expect(&format!("failed at line {}", linum));
            assert_eq!(result, first_half, "failed at line {}", linum);
        }
        for linum in 6..=15 {
            let result = get_conditional_helper(contents, &tree, linum).expect(&format!("failed at line {}", linum));
            assert_eq!(result, second_half, "failed at line {}", linum);
        }
    }

    #[test]
    fn test_fraternal_cond_block() {
        let contents = r#"
            if (cond || !(cond) && 1) {
                a = 1;
            }
            else if (cond + cond < cond) { // this is considered (else_clause (if_statement))
                a = 2;
            }
            switch (cond) {
                case 2: {
                    int c = 12;
                    a = 4 + c;
                    break;
                }
                default:
                    a = 10;
                    break;
            }
        "#;
        let mut trimmed = contents[1..].trim_end().to_string();
        trimmed.push_str("\n");
        let contents = &trimmed;
        let mut first_half = contents.split('\n').take(6).collect::<Vec<_>>().join("\n");
        first_half.push_str("\n");
        let second_half = contents.split('\n').skip(6).collect::<Vec<_>>().join("\n");
         
        let tree = QueryContext::bootstrap_tree_sitter_walk_from_str(contents).unwrap();
        for linum in 1..=6 {
            let result = get_conditional_helper(contents, &tree, linum).expect(&format!("failed at line {}", linum));
            assert_eq!(result, first_half, "failed at line {}", linum);
        }
        for linum in 7..=15 {
            let result = get_conditional_helper(contents, &tree, linum).expect(&format!("failed at line {}", linum));
            assert_eq!(result, second_half, "failed at line {}", linum);
        }
    }

    #[test]
    fn test_nested_if_block() {
        let contents = r#"
            if (cond || !(cond) && 1) {
                a = 1;
            }
            else if (cond + cond < cond) { // this is considered (else_clause (if_statement))
                if (cond && cond) {
                    a = 3;
                }
                else {
                    a = 2;
                }
            }
            else {
                a = 4;
            }
        "#;
        let mut trimmed = contents[1..].trim_end().to_string();
        trimmed.push_str("\n");
        let contents = &trimmed;
        let mut inner = contents.split('\n').skip(4).take(6).collect::<Vec<_>>().join("\n");
        inner.push_str("\n");
         
        let tree = QueryContext::bootstrap_tree_sitter_walk_from_str(contents).unwrap();
        for linum in [1, 2, 3, 4, 11, 12, 13, 14] {
            let result = get_conditional_helper(contents, &tree, linum).expect(&format!("failed at line {}", linum));
            assert_eq!(result, trimmed, "failed at line {}", linum);
        }
        for linum in 5..11 {
            let result = get_conditional_helper(contents, &tree, linum).expect(&format!("failed at line {}", linum));
            assert_eq!(result, inner, "failed at line {}", linum);
        }
    }

    #[test]
    fn test_nested_switch_block() {
        let contents = r#"
            switch (cond) {
                case 1:
                    switch (cond2) {
                        case 1:
                            a = 3;
                            break;
                    }
                    break;
                case 2: {
                    int c = 12;
                    a = 4 + c;
                    break;
                }
                default:
                    a = 10;
                    break;
            }
        "#;
        let mut trimmed = contents[1..].trim_end().to_string();
        trimmed.push_str("\n");
        let contents = &trimmed;
        let mut inner = contents.split('\n').skip(2).take(5).collect::<Vec<_>>().join("\n");
        inner.push_str("\n");
         
        let tree = QueryContext::bootstrap_tree_sitter_walk_from_str(contents).unwrap();
        for linum in [1, 2, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17] {
            let result = get_conditional_helper(contents, &tree, linum).expect(&format!("failed at line {}", linum));
            assert_eq!(result, trimmed, "failed at line {}", linum);
        }
        for linum in 3..8 {
            let result = get_conditional_helper(contents, &tree, linum).expect(&format!("failed at line {}", linum));
            assert_eq!(result, inner, "failed at line {}", linum);
        }
    }
}
