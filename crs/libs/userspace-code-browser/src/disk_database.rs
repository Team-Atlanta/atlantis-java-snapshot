use indradb::{self, QueryExt};
use anyhow::Result;
use uuid::Uuid;
use std::path::Path;
use std::collections::HashSet;

use crate::types::CodeDefinition;
use crate::database_types::{DatabaseQuery, GraphIdentifier};

#[allow(dead_code)]
pub const DEFAULT_DB_LOCATION: &str = "./project_db";

pub struct GenericDatabase<T: indradb::Datastore> {
    db: indradb::Database<T>,
}

impl<T> DatabaseQuery for GenericDatabase<T>
where T: indradb::Datastore {}

impl<T> GenericDatabase<T>
where
    T: indradb::Datastore,
{
    fn add_name(&self, funcname: &str) -> Result<indradb::Vertex> {
        let id = Self::create_named_vertex_id(funcname);
        let t = Self::create_identifier(GraphIdentifier::VertexSymbolName)?;
        let mut vertex = indradb::Vertex::with_id(id, t);
        let created = self.db.create_vertex(&vertex)?;
        let vertex_query = indradb::SpecificVertexQuery::single(id);
        if !created {
            let output = self.db.get(vertex_query.clone())?;
            let vertex_response = indradb::util::extract_vertices(output.clone());
            let vertices = vertex_response.expect("Vertex is supposed to exist");
            assert_eq!(vertices.len(), 1, "Vertex query should only return one");
            vertex = vertices[0].clone();
        }
        Ok(vertex)
    }

    fn add_edge(
        &self,
        edge_idt: GraphIdentifier,
        out_id: Uuid,
        in_id: Uuid
    ) -> Result<()> {
        let edge_t = Self::create_identifier(edge_idt)?;
        let edge = indradb::Edge::new(out_id, edge_t, in_id);
        let created = self.db.create_edge(&edge)?;
        assert!(created, "Creating duplicate edge");
        Ok(())
    }

    fn add_definition(
        &self,
        definition: &CodeDefinition,
        def_vertex_idt: GraphIdentifier,
        def_prop_vertex_idt: GraphIdentifier,
        def_edge_idt: GraphIdentifier,
        ref_edge_idt: GraphIdentifier,
    ) -> Result<()> {
        // Create a function name vertex
        let name_vertex = self.add_name(&definition.name)?;

        // Create function definition vertex and add properties
        let def_id = Self::create_random_vertex_id();
        // Create new vertex in DB
        let def_t = Self::create_identifier(def_vertex_idt)?;
        let def_vertex = indradb::Vertex::with_id(def_id, def_t);
        let created = self.db.create_vertex(&def_vertex)?;
        assert!(created, "Creating duplicate id function definition vertex");
        // Add properties
        let vertex_query = indradb::SpecificVertexQuery::single(def_id);
        let property = Some(serde_json::to_value(definition)?);
        if let Some(prop_value) = property {
            self.db.set_properties(
                vertex_query,
                Self::create_identifier(def_prop_vertex_idt)?,
                &indradb::Json::new(prop_value),
            )?;
        }

        // Associate function name vertex to function definition vertex
        self.add_edge(def_edge_idt, name_vertex.id, def_vertex.id)?;

        // Add the references
        for ref_ in definition.references.iter() {
            let in_vertex = self.add_name(ref_)?;
            self.add_edge(ref_edge_idt, def_vertex.id, in_vertex.id)?;
        }

        Ok(())
    }

    // DEBUG
    pub fn _print_all_functions(&self) -> Result<()> {
        let func_def_identifier = Self::create_identifier(GraphIdentifier::VertexFunctionDefinitionProperty)?;
        let vertex_query = indradb::VertexWithPropertyPresenceQuery::new(func_def_identifier);
        // NOTE use the methods from QueryExt to extend the query
        let vertex_query = vertex_query.properties()?;
        let output = self.db.get(vertex_query)?;
        let vertex_response = indradb::util::extract_vertices(output.clone());
        if let Some(vertices) = vertex_response {
            println!("{:?}", vertices);
        }
        let property_response = indradb::util::extract_vertex_properties(output);
        if let Some(properties) = property_response {
            for property in properties {
                for prop in &property.props {
                    let val_clone = (*prop.value).clone();
                    let funcdef: CodeDefinition = serde_json::from_value(val_clone)?;
                    println!("debug get_function_definition {} {}", funcdef.name, &funcdef.definition[..10]);
                }
            }
        }
        Ok(())
    }

    pub fn add_function_definition(&self, definition: &CodeDefinition) -> Result<()> {
        self.add_definition(
            definition,
            GraphIdentifier::VertexFunctionDefinition,
            GraphIdentifier::VertexFunctionDefinitionProperty,
            GraphIdentifier::EdgeFunctionDefinition,
            GraphIdentifier::EdgeFunctionReference
        )
    }

    pub fn add_struct_definition(&self, definition: &CodeDefinition) -> Result<()> {
        self.add_definition(
            definition,
            GraphIdentifier::VertexStructDefinition,
            GraphIdentifier::VertexStructDefinitionProperty,
            GraphIdentifier::EdgeStructDefinition,
            GraphIdentifier::EdgeStructReference
        )
    }
    
    pub fn add_enum_definition(&self, definition: &CodeDefinition) -> Result<()> {
        self.add_definition(
            definition,
            GraphIdentifier::VertexEnumDefinition,
            GraphIdentifier::VertexEnumDefinitionProperty,
            GraphIdentifier::EdgeEnumDefinition,
            GraphIdentifier::EdgeEnumReference
        )
    }

    pub fn add_union_definition(&self, definition: &CodeDefinition) -> Result<()> {
        self.add_definition(
            definition,
            GraphIdentifier::VertexUnionDefinition,
            GraphIdentifier::VertexUnionDefinitionProperty,
            GraphIdentifier::EdgeUnionDefinition,
            GraphIdentifier::EdgeUnionReference
        )
    }
    
    pub fn add_typedef_definition(&self, definition: &CodeDefinition) -> Result<()> {
        self.add_definition(
            definition,
            GraphIdentifier::VertexTypedefDefinition,
            GraphIdentifier::VertexTypedefDefinitionProperty,
            GraphIdentifier::EdgeTypedefDefinition,
            GraphIdentifier::EdgeTypedefReference
        )
    }
    
    pub fn add_preproc_definition(&self, definition: &CodeDefinition) -> Result<()> {
        self.add_definition(
            definition,
            GraphIdentifier::VertexPreprocDefinition,
            GraphIdentifier::VertexPreprocDefinitionProperty,
            GraphIdentifier::EdgePreprocDefinition,
            GraphIdentifier::EdgePreprocReference
        )
    }

    fn trace_vertex_name_to_def(&self, funcname: &str, def_idt: GraphIdentifier, backward: bool) -> Result<Vec<CodeDefinition>> {
        let mut function_definitions = vec![];

        let vertex_query = Self::trace_helper_get_vertices_query(funcname, backward)?;
        let output = self.db.get(vertex_query)?;
        let edge_response = indradb::util::extract_edges(output);

        if let Some(edges) = edge_response {
            for edge in edges {
                let vertex_query = Self::trace_helper_get_neighbour_properties_query(&edge, backward)?;
                let output = self.db.get(vertex_query)?;
                let property_response = indradb::util::extract_vertex_properties(output);

                if let Some(properties) = property_response {
                    let tmp_definitions = Self::collect_matching_idt_definitions(&properties, def_idt)?;
                    function_definitions.extend(tmp_definitions);
                }
            }
        }
        Ok(function_definitions)
    }

    fn get_function_definition_helper(&self, funcname: &str, visited: &mut HashSet<String>) -> Result<Vec<CodeDefinition>> {
        let mut ret = vec![];
        let preprocs = self.trace_vertex_name_to_def(funcname, GraphIdentifier::VertexPreprocDefinitionProperty, false)?;
        let funcs = self.trace_vertex_name_to_def(funcname, GraphIdentifier::VertexFunctionDefinitionProperty, false)?;
        visited.insert(funcname.to_string());
        ret.extend(funcs);
        for preproc in preprocs.iter() {
            for r in preproc.references.iter() {
                if visited.contains(r) {
                    continue;
                }
                let subcall = self.get_function_definition_helper(&r, visited)?;
                ret.extend(subcall);
            }
        }
        ret.extend(preprocs);
        Ok(ret)
    }

    pub fn get_function_definition(&self, funcname: &str) -> Result<Vec<CodeDefinition>> {
        self.get_function_definition_helper(funcname, &mut HashSet::from([]))
    }

    pub fn get_function_cross_references(&self, funcname: &str) -> Result<Vec<CodeDefinition>> {
        let mut ret = vec![];
        ret.extend(self.trace_vertex_name_to_def(funcname, GraphIdentifier::VertexFunctionDefinitionProperty, true)?);
        ret.extend(self.trace_vertex_name_to_def(funcname, GraphIdentifier::VertexPreprocDefinitionProperty, true)?);
        Ok(ret)
    }

    pub fn get_struct_definition(&self, typename: &str) -> Result<Vec<CodeDefinition>> {
        self.trace_vertex_name_to_def(typename, GraphIdentifier::VertexStructDefinitionProperty, false)
    }

    pub fn get_enum_definition(&self, typename: &str) -> Result<Vec<CodeDefinition>> {
        self.trace_vertex_name_to_def(typename, GraphIdentifier::VertexEnumDefinitionProperty, false)
    }

    pub fn get_union_definition(&self, typename: &str) -> Result<Vec<CodeDefinition>> {
        self.trace_vertex_name_to_def(typename, GraphIdentifier::VertexUnionDefinitionProperty, false)
    }

    pub fn get_typedef_definition(&self, typename: &str) -> Result<Vec<CodeDefinition>> {
        self.trace_vertex_name_to_def(typename, GraphIdentifier::VertexTypedefDefinitionProperty, false)
    }

    pub fn get_any_type_definition(&self, typename: &str) -> Result<Vec<CodeDefinition>> {
        // NOTE most efficient is to change property lookup in trace_vertex_name_to_def
        let mut ret = vec![];
        ret.extend(self.get_struct_definition(typename)?);
        ret.extend(self.get_enum_definition(typename)?);
        ret.extend(self.get_union_definition(typename)?);
        ret.extend(self.get_typedef_definition(typename)?);
        Ok(ret)
    }
}


#[allow(dead_code)]
pub type MemoryDatabase = GenericDatabase<indradb::MemoryDatastore>;

#[cfg(feature = "standalone")]
#[allow(dead_code)]
pub type DiskDatabase = GenericDatabase<indradb::RocksdbDatastore>;

#[cfg(feature = "standalone")]
impl GenericDatabase<indradb::RocksdbDatastore> {
    pub fn new(path: &Path) -> Self {
        Self {
            db: indradb::RocksdbDatastore::new_db(path).expect("database couldn't be created")
        }
    }
}

impl GenericDatabase<indradb::MemoryDatastore> {
    #[allow(dead_code)]
    pub fn new() -> Self {
        Self { db: indradb::MemoryDatastore::new_db() }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;
    use crate::types::CodeDefinitionType;

    #[test]
    fn test_insert_and_get() {
        // NOTE when adding a new type of definition, add the getter and setter to this list
        let basic_methods: Vec<(Box<dyn Fn(&MemoryDatabase, &str) -> Result<Vec<CodeDefinition>>>, Box<dyn Fn(&MemoryDatabase, &CodeDefinition) -> Result<()>>)> = vec![
            (Box::new(|db, name| db.get_function_definition(name)),
                Box::new(|db, def| db.add_function_definition(def))),
            (Box::new(|db, name| db.get_struct_definition(name)),
                Box::new(|db, def| db.add_struct_definition(def))),
            (Box::new(|db, name| db.get_enum_definition(name)),
                Box::new(|db, def| db.add_enum_definition(def))),
            (Box::new(|db, name| db.get_union_definition(name)),
                Box::new(|db, def| db.add_union_definition(def))),
            (Box::new(|db, name| db.get_typedef_definition(name)),
                Box::new(|db, def| db.add_typedef_definition(def))),
        ];
        let name = "foo";
        for (i, method) in basic_methods.iter().enumerate() {
            let db = MemoryDatabase::new();
            let definition = CodeDefinition { // doesn't actually matter what contents are
                name: name.to_string(),
                definition: "int foo() { return 1; }".to_string(),
                filename: "testfile".to_string(),
                references: vec![],
                def_type: CodeDefinitionType::Function,
            };

            // make sure everything reports empty
            for method_inner in basic_methods.iter() {
                assert_eq!(method_inner.0(&db, name).unwrap().len(), 0);
            }

            // add definition
            method.1(&db, &definition).unwrap();

            // make sure only corresponding getter returns the definition
            for (j, method_inner) in basic_methods.iter().enumerate() {
                if i != j {
                    assert_eq!(method_inner.0(&db, name).unwrap().len(), 0);
                }
                else {
                    let defs = method_inner.0(&db, name).unwrap();
                    assert_eq!(defs.len(), 1);
                    assert_eq!(defs[0], definition);
                }
            }
        }
    }

    #[test]
    fn test_xref() {
        let definitions: Vec<_> = vec![
            ("foo", vec!["foo", "bar", "baz"]),
            ("bar", vec!["foo"]),
            ("baz", vec!["bar"]),
            ("qux", vec!["foo"]),
            ("quux", vec![]),
        ].into_iter().map(|(name, refs)| {
            CodeDefinition {
                name: name.to_string(),
                definition: "".to_string(),
                filename: "".to_string(),
                references: refs.into_iter().map(|x| x.to_string()).collect(),
                def_type: CodeDefinitionType::Function,
            }
        }).collect();

        let truths = vec![
            vec!["foo", "bar", "qux"],
            vec!["foo", "baz"],
            vec!["foo"],
            vec![],
            vec![],
        ];

        let db = MemoryDatabase::new();
        for def in definitions.iter() {
            db.add_function_definition(def).unwrap();
        }
        let xrefs: Vec<Vec<_>> = definitions.iter().map(|def| {
            db.get_function_cross_references(&def.name).unwrap().iter().map(|r| {
                r.name.clone()
            }).collect()
        }).collect();

        assert_eq!(xrefs.len(), truths.len());
        for i in 0..xrefs.len() {
            assert_eq!(
                xrefs[i].len(),
                truths[i].len()
            );
            assert_eq!(
                xrefs[i].iter().cloned().collect::<HashSet<_>>(),
                truths[i].iter().map(|s| s.to_string()).collect::<HashSet<_>>()
            );
        }
    }

    #[test]
    fn test_any_type() {
        let name = "something";
        let definitions: Vec<_> = vec![
            "some_function",
            "some_struct",
            "some_enum",
            "some_union",
            "some_typedef",
        ].into_iter().map(|def| {
            CodeDefinition {
                name: name.to_string(),
                definition: def.to_string(),
                filename: "".to_string(),
                references: vec![],
                def_type: CodeDefinitionType::Function, // FIXME not that it matters...
            }
        }).collect();
        let db = MemoryDatabase::new();
        db.add_function_definition(&definitions[0]).unwrap();
        db.add_struct_definition(&definitions[1]).unwrap();
        db.add_enum_definition(&definitions[2]).unwrap();
        db.add_union_definition(&definitions[3]).unwrap();
        db.add_typedef_definition(&definitions[4]).unwrap();
        let any_type_defs = db.get_any_type_definition(name).unwrap();
        assert_eq!(any_type_defs.len(), 4);
        let result_set: HashSet<_> = any_type_defs.iter().map(|d| d.definition.clone()).collect();
        let truth: HashSet<_> = definitions.iter().skip(1).map(|d| d.definition.clone()).collect();
        assert_eq!(result_set, truth);
    }

    #[test]
    fn test_preproc() {
        let db = MemoryDatabase::new();
        db.add_function_definition(
            &CodeDefinition {
                name: "__parse_csv_record".to_string(),
                definition: "csv_record *__parse_csv_record(const str *in, enum csv_flags parse_flags, unsigned char sep);".to_string(),
                filename: "".to_string(),
                references: vec!["irrelevant_function".to_string()],
                def_type: CodeDefinitionType::Function,
            },
        ).unwrap();
        db.add_preproc_definition(
            &CodeDefinition {
                name: "_parse_csv_record".to_string(),
                definition: "#define _parse_csv_record(in, flags) __parse_csv_record(in, flags, ',')\n".to_string(),
                filename: "".to_string(),
                references: vec!["__parse_csv_record".to_string()],
                def_type: CodeDefinitionType::Preproc,
            },
        ).unwrap();
        db.add_preproc_definition(
            &CodeDefinition {
                name: "parse_csv_record".to_string(),
                definition: "#define parse_csv_record(in) _parse_csv_record(in, 0)\n".to_string(),
                filename: "".to_string(),
                references: vec!["_parse_csv_record".to_string()],
                def_type: CodeDefinitionType::Preproc,
            },
        ).unwrap();
        db.add_function_definition(
            &CodeDefinition {
                name: "irrelevant_function".to_string(),
                definition: "void irrelevant_function() {}".to_string(),
                filename: "".to_string(),
                references: vec![],
                def_type: CodeDefinitionType::Function,
            },
        ).unwrap();
        // cycle happens if preproc defines, then we undef and define func (thank you aout_volume_New, you cursed beauty)
        db.add_preproc_definition(
            &CodeDefinition {
                name: "recursive_preproc".to_string(),
                definition: "#define recursive_preproc recursive_preproc()".to_string(),
                filename: "".to_string(),
                references: vec!["recursive_preproc".to_string()],
                def_type: CodeDefinitionType::Preproc,
            },
        ).unwrap();

        let defs = db.get_function_definition("parse_csv_record").unwrap();
        assert_eq!(defs.len(), 3);
        assert_eq!(
            defs.into_iter().map(|d| d.name.clone()).collect::<HashSet<_>>(),
            HashSet::from([
                "__parse_csv_record".to_string(),
                "_parse_csv_record".to_string(),
                "parse_csv_record".to_string(),
            ])
        );

        let defs = db.get_function_definition("_parse_csv_record").unwrap();
        assert_eq!(defs.len(), 2);
        assert_eq!(
            defs.into_iter().map(|d| d.name.clone()).collect::<HashSet<_>>(),
            HashSet::from([
                "__parse_csv_record".to_string(),
                "_parse_csv_record".to_string(),
            ])
        );

        let defs = db.get_function_definition("__parse_csv_record").unwrap();
        assert_eq!(defs.len(), 1);
        assert_eq!(defs[0].name, "__parse_csv_record");

        let defs = db.get_function_definition("recursive_preproc").unwrap();
        assert_eq!(defs.len(), 1);
        assert_eq!(defs[0].name, "recursive_preproc");

        let xrefs = db.get_function_cross_references("parse_csv_record").unwrap();
        assert_eq!(xrefs.len(), 0);

        let xrefs = db.get_function_cross_references("_parse_csv_record").unwrap();
        assert_eq!(xrefs.len(), 1);
        assert_eq!(xrefs[0].name, "parse_csv_record");

        let xrefs = db.get_function_cross_references("__parse_csv_record").unwrap();
        assert_eq!(xrefs.len(), 1);
        assert_eq!(xrefs[0].name, "_parse_csv_record");

        let xrefs = db.get_function_cross_references("irrelevant_function").unwrap();
        assert_eq!(xrefs.len(), 1);
        assert_eq!(xrefs[0].name, "__parse_csv_record");

        let xrefs = db.get_function_cross_references("recursive_preproc").unwrap();
        assert_eq!(xrefs.len(), 1);
        assert_eq!(xrefs[0].name, "recursive_preproc");
    }
}
