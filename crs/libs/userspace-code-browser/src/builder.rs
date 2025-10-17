use tree_sitter::{TreeCursor, Query, QueryCursor, QueryCapture, Node};
use streaming_iterator::StreamingIterator;
use anyhow::Result;
use rayon::prelude::*;
use std::collections::LinkedList;
use std::collections::HashSet;
use regex::Regex;
use indradb;
use std::marker::{Send, Sync};
use std::path::{Path, PathBuf};

use crate::disk_database::GenericDatabase;
use crate::types::{CodeDefinition, CodeDefinitionBuilder, CodeDefinitionType};
use crate::tree_sitter_helper::{QueryContext, TreeSitterTraversal, node_to_string, node_option_to_string, node_to_multiline_string, try_read_file};
use crate::walker::get_all_c_paths;

fn get_references_in_def(qc: &QueryContext, node: Node, content_bytes: &[u8]) -> Vec<String> {
    let mut qcursor = QueryCursor::new();
    let ref_query = qc.get_query_c_function_references();
    let captures = qcursor.captures(ref_query, node, content_bytes);
    let mut references = HashSet::new();
    captures.for_each(|(query_match, _)| {
        assert_eq!(query_match.captures.len(), 1, "Capture is not len 1 {:?}", query_match.captures);
        let capture = query_match.captures[0];
        let node = capture.node;
        let text = node_to_string(node, content_bytes);
        if !text.is_empty() {
            references.insert(text.to_string());
        }
    });

    references.into_iter().collect()
}

// NOTE walking cus parenthesized declarator doesn't follow capture pattern
fn get_declaration_in_def(node: Node, content_bytes: &[u8]) -> String {
    let mut tcursor = node.walk();

    let traverse_field = TreeSitterTraversal::new(|cursor: &TreeCursor, field: &str| {
        cursor.field_name() == Some(field)
    });
    let traverse_grammar = TreeSitterTraversal::new(|cursor: &TreeCursor, field: &str| {
        cursor.node().grammar_name() == field
    });
    
    let node_opt = traverse_field.dfs(&mut tcursor, "declarator");
    if node_opt.is_none() {
        return "".to_string();
    }
    let node = node_opt.unwrap();

    let mut tcursor = node.walk();
    let node_opt = traverse_grammar.dfs(&mut tcursor, "identifier");
    node_option_to_string(node_opt, content_bytes)
}

fn get_comments_before_def(root_node: Node, func_node: Node, content_bytes: &[u8]) -> String {
    let mut collection = LinkedList::new();
    
    let mut tcursor = root_node.walk();
    let traverse = TreeSitterTraversal::new(|cursor: &TreeCursor, node: &Node| -> bool {
        cursor.node() == *node
    });
    let node_opt = traverse.dfs(&mut tcursor, &func_node);
    if node_opt.is_none() {
        return "".to_string();
    }

    loop {
        let success = tcursor.goto_previous_sibling();
        if !success || tcursor.node().grammar_name() != "comment" {
            break;
        }
        collection.push_front(node_to_multiline_string(tcursor.node(), content_bytes));
    }
    let _node = node_opt.unwrap();

    collection.into_iter().collect::<Vec<String>>().join("")
}

fn handle_function(qc: &QueryContext, content_bytes: &[u8], root_node: Node, capture: &QueryCapture, builder: &mut CodeDefinitionBuilder) {
    let node = capture.node;
    let mut definition_builder = get_comments_before_def(root_node, node, content_bytes);
    let definition = node_to_multiline_string(node, content_bytes);
    definition_builder.push_str(&definition);
    let name = get_declaration_in_def(node, content_bytes);
    let references = get_references_in_def(qc, node, content_bytes);
    builder.set_name(name);
    builder.set_definition(definition_builder);
    builder.set_references(references);
}

fn handle_type(def_query: &Query, content_bytes: &[u8], capture: &QueryCapture, builder: &mut CodeDefinitionBuilder) {
    let node = capture.node;
    let text = node_to_string(node, content_bytes);
    let multiline = node_to_multiline_string(node, content_bytes);
    match def_query.capture_names()[capture.index as usize] {
        "name" => builder.set_name(text.to_string()),
        "definition" => builder.set_definition(multiline),
        _ => (), // NOTE how useful are references?
    }
}

fn handle_preproc(def_query: &Query, content_bytes: &[u8], capture: &QueryCapture, builder: &mut CodeDefinitionBuilder) {
    let node = capture.node;
    let text = node_to_string(node, content_bytes);
    match def_query.capture_names()[capture.index as usize] {
        "name" => builder.set_name(text.to_string()),
        "definition" => builder.set_definition(text.to_string()),
        "value" => {
            let re = Regex::new(r"^(?<name>[a-zA-Z0-9_]+)\(.*\)$").expect("Regex construction");
            let refs = match re.captures(&text) {
                Some(caps) => {
                    vec![caps["name"].to_string()]
                }
                None => {
                    vec![]
                }
            };
            builder.set_references(refs);
        }
        _ => (),
    }
}

fn capture_c(qc: &QueryContext, qcursor: &mut QueryCursor, node: Node, content_bytes: &[u8], filename: &str) -> Vec<CodeDefinition> {
    let mut definitions = vec![];
    let def_query = qc.get_query_c_all();
    let mut captures = qcursor.captures(def_query, node, content_bytes);
    let mut builders = vec![];

    while let Some((query_match, idx)) = captures.next() {
        let query_id = query_match.id() as usize;
        assert!(builders.len() >= query_id,
            "match id is too large compared to builders");
        if builders.len() == query_id {
            assert_eq!(*idx, 0);
            let mut builder = CodeDefinitionBuilder::default();
            builder.set_filename(filename.to_string());
            if query_match.pattern_index == CodeDefinitionType::Function as usize {
                assert_eq!(*idx, 0, "Query match idx not zero");
                assert_eq!(query_match.captures.len(), 1, "Query match not one capture {:?}", query_match.captures);
                builder.set_type(CodeDefinitionType::Function);
            }
            else if query_match.pattern_index == CodeDefinitionType::Struct as usize {
                builder.set_type(CodeDefinitionType::Struct);
                builder.set_references(vec![]);
            }
            else if query_match.pattern_index == CodeDefinitionType::Enum as usize {
                builder.set_type(CodeDefinitionType::Enum);
                builder.set_references(vec![]);
            }
            else if query_match.pattern_index == CodeDefinitionType::Union as usize {
                builder.set_type(CodeDefinitionType::Union);
                builder.set_references(vec![]);
            }
            else if query_match.pattern_index == CodeDefinitionType::Typedef as usize {
                builder.set_type(CodeDefinitionType::Typedef);
                builder.set_references(vec![]);
            }
            else if query_match.pattern_index == CodeDefinitionType::Preproc as usize {
                builder.set_type(CodeDefinitionType::Preproc);
            }
            builders.push(Some(builder));
        }

        assert!(builders.len() > query_id, "builders length after supposed new push");
        let builder = &mut builders[query_id].as_mut().expect("Builder should be processable");
        assert!(!builder.is_ready());

        let capture = query_match.captures[*idx];

        if query_match.pattern_index == CodeDefinitionType::Function as usize {
            assert_eq!(builder.def_type, Some(CodeDefinitionType::Function));
            handle_function(qc, content_bytes, node, &capture, builder);
        }
        else if query_match.pattern_index == CodeDefinitionType::Struct as usize {
            assert_eq!(builder.def_type, Some(CodeDefinitionType::Struct));
            assert!(*idx == 0 || *idx == 1, "Unexpected query match idx");
            handle_type(def_query, content_bytes, &capture, builder);
        }
        else if query_match.pattern_index == CodeDefinitionType::Enum as usize {
            assert_eq!(builder.def_type, Some(CodeDefinitionType::Enum));
            assert!(*idx == 0 || *idx == 1, "Unexpected query match idx");
            handle_type(def_query, content_bytes, &capture, builder);
        }
        else if query_match.pattern_index == CodeDefinitionType::Union as usize {
            assert_eq!(builder.def_type, Some(CodeDefinitionType::Union));
            assert!(*idx == 0 || *idx == 1, "Unexpected query match idx");
            handle_type(def_query, content_bytes, &capture, builder);
        }
        else if query_match.pattern_index == CodeDefinitionType::Typedef as usize {
            assert_eq!(builder.def_type, Some(CodeDefinitionType::Typedef));
            assert!(*idx == 0 || *idx == 1, "Unexpected query match idx");
            handle_type(def_query, content_bytes, &capture, builder);
        }
        else if query_match.pattern_index == CodeDefinitionType::Preproc as usize {
            assert_eq!(builder.def_type, Some(CodeDefinitionType::Preproc));
            assert!(*idx <= 2, "Unexpected query match idx");
            handle_preproc(def_query, content_bytes, &capture, builder);
        }

        let result = builder.is_ready();
        if result {
            let mut builder_swap = None;
            std::mem::swap(&mut builder_swap, &mut builders[query_id]);
            let builder = builder_swap.expect("Swapped builder should be unwrappable");
            let codedef = builder.build().expect("Unwrap builder failed even though we checked is_ready");
            definitions.push(codedef);
        }
    };
    definitions
}

fn parse_c_procedure<T>(file_contents: &str, filename: &str, db: &GenericDatabase<T>) -> Result<()>
where T: indradb::Datastore
{
    
    let (tree, qc, mut qcursor) = QueryContext::bootstrap_tree_sitter_parse_from_str(&file_contents)?;
    let content_bytes = file_contents.as_bytes();
    let root_node = tree.root_node();

    let definitions = capture_c(
        &qc,
        &mut qcursor,
        root_node,
        content_bytes,
        filename
    );
    for d in definitions {
        let result = match d.def_type {
            CodeDefinitionType::Function => db.add_function_definition(&d),
            CodeDefinitionType::Struct => db.add_struct_definition(&d),
            CodeDefinitionType::Enum => db.add_enum_definition(&d),
            CodeDefinitionType::Union => db.add_union_definition(&d),
            CodeDefinitionType::Typedef => db.add_typedef_definition(&d),
            CodeDefinitionType::Preproc => db.add_preproc_definition(&d),
        };
        if result.is_err() {
            eprintln!("Error inserting {:?} into db", d);
        }
    }

    Ok(())
}

/// Removes code blocks from preprocessor expanded output that don't belong to the target file.
/// Lines starting with # [number] "[filename]" indicate the start of code blocks.
/// Only keeps code blocks where [filename] matches the target filename.
/// Example # 1 "src/core/ngx_regex.c"
fn cleanup_after_expansion(content: &str, filename: &str) -> String {
    let mut result = String::new();
    let mut skip_lines = false;
    
    for line in content.lines() {
        let mut skip_current_line = false;
        if line.starts_with("# ") {
            skip_lines = true;
            let parts: Vec<&str> = line.split_whitespace().collect();
            if parts.len() >= 3 {
                // Format is # [number] "[filename]"
                let linenum_ok = parts[1].parse::<u64>().is_ok();
                let quoted = parts[2];
                let is_quoted = quoted.starts_with('"') && quoted.ends_with('"');
                if linenum_ok && is_quoted {
                    let current_file = quoted.trim_matches('"');

                    let current_path = Path::new(current_file);
                    let filename_path = Path::new(&filename);

                    let matches_file = filename_path.ends_with(current_path);
                    let is_relative = current_file.starts_with('.');

                    if matches_file || is_relative {
                        skip_lines = false;
                    }
                }
            }
            skip_current_line = true;
        }
        
        if !(skip_lines || skip_current_line) {
            result.push_str(line);
            result.push('\n');
        }
    }
    
    result
}

pub fn main_build<T>(db: &GenericDatabase<T>, root_path: &str)
where T: indradb::Datastore + Send + Sync
{
    println!("Building index for {}", root_path);
    let all_c_paths = get_all_c_paths(&root_path);
    let root_path = match PathBuf::from(root_path).canonicalize() {
        Ok(path) => path,
        Err(err) => {
            eprintln!("Failed to canonicalize root path: {err}");
            return;
        }
    };
    all_c_paths.par_iter().for_each(|canonical_path_str| {
        let canonical_path = Path::new(canonical_path_str);
        let file_contents_res = try_read_file(canonical_path_str);
        if let Ok(file_contents) = file_contents_res {
            let relative_path = canonical_path.strip_prefix(&root_path).unwrap_or(canonical_path);
            let relative_path_str = relative_path.to_str().unwrap_or(canonical_path_str);
            // NOTE if causes issues, simply remove the cleanup call here
            // let cleaned_contents = cleanup_after_expansion(&file_contents, canonical_path_str);
            let cleaned_contents = file_contents;
            let result = parse_c_procedure(&cleaned_contents, relative_path_str, db);
            if result.is_err() {
                eprintln!("Error parsing {}", canonical_path_str);
            }
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_function_references() {
        let content_str = r#"
            aout_volume_t *aout_volume_New(vlc_object_t *parent,
                                        const audio_replay_gain_t *gain)
            {
                aout_volume_t *vol = vlc_custom_create(parent, sizeof (aout_volume_t),
                                                    "volume");
                if (unlikely(vol == NULL))
                    return NULL;
                vol->module = NULL;
                atomic_init(&vol->gain_factor, 1.f);
                atomic_init(&vol->output_factor, 1.f);

                //audio_volume_t *obj = &vol->object;

                /* Gain */
                if (gain != NULL)
                    memcpy(&vol->replay_gain, gain, sizeof (vol->replay_gain));
                else
                    memset(&vol->replay_gain, 0, sizeof (vol->replay_gain));

                var_AddCallback(parent, "audio-replay-gain-mode",
                                ReplayGainCallback, vol);
                var_TriggerCallback(parent, "audio-replay-gain-mode");

                return vol;
            }
        "#;
        let content_bytes = content_str.as_bytes();
        let refs_truth: HashSet<String> = [
            "vlc_custom_create",
            "unlikely",
            "atomic_init",
            "memcpy",
            "memset",
            "var_AddCallback",
            "var_TriggerCallback"
        ].into_iter().map(|s| s.to_string()).collect();

        let (tree, qc, mut qcursor) = QueryContext::bootstrap_tree_sitter_parse_from_str(content_str).unwrap();
        let node = tree.root_node().child(0).expect("No first child in tree");
        assert_eq!(node.grammar_name(), "function_definition");

        let refs: HashSet<String> = get_references_in_def(&qc, node, content_bytes).into_iter().collect();
        assert_eq!(refs, refs_truth);

        let funcdefs = capture_c(&qc, &mut qcursor, node, content_bytes, "x");
        let mut truth = content_str[1..].trim_end().to_string();
        truth.push_str("\n");
        assert_eq!(funcdefs.len(), 1);
        assert_eq!(funcdefs[0].name, "aout_volume_New".to_string());
        assert_eq!(funcdefs[0].definition, truth);
    }

    #[test]
    fn test_function_declaration() {
        let defs_and_ids = [
            ("aout_volume_New", "aout_volume_t *aout_volume_New(vlc_object_t *parent, const audio_replay_gain_t *gain) {}"),
            ("apreq_parse_multipart", "APREQ_DECLARE_PARSER(apreq_parse_multipart) {}"),
            ("vlc_thread_set_name", "void (vlc_thread_set_name)(const char *name) {}")
        ];
        let content_str = defs_and_ids.iter().map(|&pair| pair.1).collect::<Vec<&str>>().join("\n");
        let ids_truth: Vec<String> = defs_and_ids.iter().map(|&pair| pair.0.to_string()).collect();

        let content_bytes = content_str.as_bytes();
        let tree = QueryContext::bootstrap_tree_sitter_walk_from_str(&content_str).unwrap();
        let children_count = tree.root_node().child_count();
        assert_eq!(children_count, ids_truth.len());

        let ids: Vec<String> = (0..children_count).map(|child_idx| {
            let node = tree.root_node().child(child_idx).expect(&format!("No child of index {}", child_idx));
            assert_eq!(node.grammar_name(), "function_definition");
            get_declaration_in_def(node, content_bytes)
        }).collect();
        assert_eq!(ids, ids_truth)
    }

    #[test]
    fn test_function_comments() {
        let comments = r#"
            /**
             * Do you like your multiline comments?
             * I do!
             */
            // Single line comment
        "#;
        let content_str = format!(r#"
            // Single line comment
            #define NOT_A_COMMENT
            {}
            int foo() {{}}
            #define NOT_A_COMMENT_2
        "#, comments);
        let mut truth = comments[1..].trim_end().to_string();
        truth.push_str("\n");

        let content_bytes = content_str.as_bytes();
        let tree = QueryContext::bootstrap_tree_sitter_walk_from_str(&content_str).unwrap();
        let func_node = tree.root_node().child(4).expect("Couldn't find child");
        assert_eq!(func_node.grammar_name(), "function_definition");

        let comments = get_comments_before_def(tree.root_node(), func_node, content_bytes);
        assert_eq!(comments, truth);
    }

    #[test]
    fn test_types() {
        let snippet = r#"
            struct my_struct_s {int a; char *b;};
            typedef struct my_struct_s my_struct_t;

            typedef enum my_enum_e {A, B, C} my_enum_t;

            typedef union my_union_u {int i; float f; my_struct_t t;} my_union_t;

            // ensure declarations are not caught
            void foo() {
                enum my_enum_e vare = A;
                union my_union_u varu = { .i = 1 };
                struct my_struct_s vars = { 1, "hello" };
            }
        "#;
        let content_bytes = snippet.as_bytes();

        let (tree, qc, mut qcursor) = QueryContext::bootstrap_tree_sitter_parse_from_str(snippet).unwrap();
        let root_node = tree.root_node();
        let filename = "testfile";


        let definitions = capture_c(
            &qc,
            &mut qcursor,
            root_node,
            content_bytes,
            filename
        );

        let struct_definitions: Vec<_> = definitions
            .iter()
            .filter(|d| d.def_type == CodeDefinitionType::Struct)
            .collect();
        assert_eq!(struct_definitions.len(), 1);
        assert_eq!(
            *struct_definitions[0],
            CodeDefinition {
                name: "my_struct_s".to_string(),
                definition: "            struct my_struct_s {int a; char *b;};\n".to_string(),
                filename: filename.to_string(),
                references: vec![],
                def_type: CodeDefinitionType::Struct,
            }
        );

        let enum_definitions: Vec<_> = definitions
            .iter()
            .filter(|d| d.def_type == CodeDefinitionType::Enum)
            .collect();
        assert_eq!(enum_definitions.len(), 1);
        assert_eq!(
            *enum_definitions[0],
            CodeDefinition {
                name: "my_enum_e".to_string(),
                definition: "            typedef enum my_enum_e {A, B, C} my_enum_t;\n".to_string(),
                filename: filename.to_string(),
                references: vec![],
                def_type: CodeDefinitionType::Enum,
            }
        );

        let union_definitions: Vec<_> = definitions
            .iter()
            .filter(|d| d.def_type == CodeDefinitionType::Union)
            .collect();
        assert_eq!(union_definitions.len(), 1);
        assert_eq!(
            *union_definitions[0],
            CodeDefinition {
                name: "my_union_u".to_string(),
                definition: "            typedef union my_union_u {int i; float f; my_struct_t t;} my_union_t;\n".to_string(),
                filename: filename.to_string(),
                references: vec![],
                def_type: CodeDefinitionType::Union,
            }
        );

        let typedef_definitions: Vec<_> = definitions
            .iter()
            .filter(|d| d.def_type == CodeDefinitionType::Typedef)
            .collect();
        assert_eq!(typedef_definitions.len(), 3);
        assert_eq!(
            *typedef_definitions[0],
            CodeDefinition {
                name: "my_struct_t".to_string(),
                definition: "            typedef struct my_struct_s my_struct_t;\n".to_string(),
                filename: filename.to_string(),
                references: vec![],
                def_type: CodeDefinitionType::Typedef,
            }
        );
        assert_eq!(
            *typedef_definitions[1],
            CodeDefinition {
                name: "my_enum_t".to_string(),
                definition: "            typedef enum my_enum_e {A, B, C} my_enum_t;\n".to_string(),
                filename: filename.to_string(),
                references: vec![],
                def_type: CodeDefinitionType::Typedef,
            }
        );
        assert_eq!(
            *typedef_definitions[2],
            CodeDefinition {
                name: "my_union_t".to_string(),
                definition: "            typedef union my_union_u {int i; float f; my_struct_t t;} my_union_t;\n".to_string(),
                filename: filename.to_string(),
                references: vec![],
                def_type: CodeDefinitionType::Typedef,
            }
        );
    }

    #[test]
    fn test_preproc_functions() {
        let snippet = r#"
            csv_record *__parse_csv_record(const str *in, enum csv_flags parse_flags,
                                           unsigned char sep) {}
            #define _parse_csv_record(in, flags) __parse_csv_record(in, flags, ',')
            #define parse_csv_record(in) _parse_csv_record(in, 0)
            #define not_function_call(in, flags) in + flags
        "#;
        let content_bytes = snippet.as_bytes();

        let (tree, qc, mut qcursor) = QueryContext::bootstrap_tree_sitter_parse_from_str(snippet).unwrap();
        let root_node = tree.root_node();
        let filename = "testfile";

        let definitions = capture_c(
            &qc,
            &mut qcursor,
            root_node,
            content_bytes,
            filename
        );

        let preproc_definitions: Vec<_> = definitions
            .iter()
            .filter(|d| d.def_type == CodeDefinitionType::Preproc)
            .collect();

        assert_eq!(definitions.len(), 4);
        assert_eq!(preproc_definitions.len(), 3);
        assert_eq!(
            *preproc_definitions[0],
            CodeDefinition {
                name: "_parse_csv_record".to_string(),
                definition: "#define _parse_csv_record(in, flags) __parse_csv_record(in, flags, ',')\n".to_string(),
                filename: filename.to_string(),
                references: vec!["__parse_csv_record".to_string()],
                def_type: CodeDefinitionType::Preproc,
            }
        );
        assert_eq!(
            *preproc_definitions[1],
            CodeDefinition {
                name: "parse_csv_record".to_string(),
                definition: "#define parse_csv_record(in) _parse_csv_record(in, 0)\n".to_string(),
                filename: filename.to_string(),
                references: vec!["_parse_csv_record".to_string()],
                def_type: CodeDefinitionType::Preproc,
            }
        );
        assert_eq!(
            *preproc_definitions[2],
            CodeDefinition {
                name: "not_function_call".to_string(),
                definition: "#define not_function_call(in, flags) in + flags\n".to_string(),
                filename: filename.to_string(),
                references: vec![],
                def_type: CodeDefinitionType::Preproc,
            }
        );
    }
}
