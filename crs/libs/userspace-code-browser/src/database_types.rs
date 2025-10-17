use strum_macros;
use anyhow::Result;
use uuid::Uuid;
use indradb::{self, QueryExt, PipeQuery, PipePropertyQuery, Edge, VertexProperties};
use serde_json;

use crate::types::CodeDefinition;

#[allow(dead_code)]
#[derive(strum_macros::Display, Clone, Copy)]
pub(crate) enum GraphIdentifier {
    VertexSymbolName,

    VertexFunctionDefinition,
    VertexFunctionDefinitionProperty,
    EdgeFunctionDefinition,
    EdgeFunctionReference,

    VertexStructDefinition,
    VertexStructDefinitionProperty,
    EdgeStructDefinition,
    EdgeStructReference,

    VertexEnumDefinition,
    VertexEnumDefinitionProperty,
    EdgeEnumDefinition,
    EdgeEnumReference,

    VertexUnionDefinition,
    VertexUnionDefinitionProperty,
    EdgeUnionDefinition,
    EdgeUnionReference,

    VertexTypedefDefinition,
    VertexTypedefDefinitionProperty,
    EdgeTypedefDefinition,
    EdgeTypedefReference,
    
    VertexPreprocDefinition,
    VertexPreprocDefinitionProperty,
    EdgePreprocDefinition,
    EdgePreprocReference,
}

#[allow(dead_code)]
pub(crate) trait DatabaseQuery {
    fn create_identifier(t: GraphIdentifier) -> Result<indradb::Identifier> {
        let s = t.to_string();
        Ok(indradb::Identifier::new(&s)?)
    }

    fn create_named_vertex_id(name: &str) -> Uuid {
        Uuid::new_v5(&Uuid::NAMESPACE_DNS, name.as_bytes())
    }

    fn create_random_vertex_id() -> Uuid {
        Uuid::new_v4()
    }

    fn trace_helper_get_vertices_query(funcname: &str, backward: bool) -> Result<PipeQuery> {
        let id = Self::create_named_vertex_id(funcname);
        let vertex_query = indradb::SpecificVertexQuery::single(id);
        let vertex_query = if backward {
            vertex_query.inbound()
        }
        else {
            vertex_query.outbound()
        }?;

        Ok(vertex_query)
    }

    fn trace_helper_get_neighbour_properties_query(edge: &Edge, backward: bool) -> Result<PipePropertyQuery> {
        let other_vertex = if backward {
            edge.outbound_id
        } else {
            edge.inbound_id
        };
        let vertex_query = indradb::SpecificVertexQuery::single(other_vertex).properties()?;
        Ok(vertex_query)
    }

    fn collect_matching_idt_definitions(properties: &[VertexProperties], def_idt: GraphIdentifier) -> Result<Vec<CodeDefinition>> {
        let mut definitions = vec![];
        let func_def_identifier = Self::create_identifier(def_idt)?;
        assert_eq!(properties.len(), 1, "Number of properties from func def vertex");
        for prop in &properties[0].props {
            if func_def_identifier == prop.name {
                let val_clone = (*prop.value).clone();
                let funcdef: CodeDefinition = serde_json::from_value(val_clone)?;
                definitions.push(funcdef);
            }
        }
        Ok(definitions)
    }

}
