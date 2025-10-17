use indradb;
use indradb_proto as proto;
use anyhow::Result;
use std::collections::HashSet;

use crate::types::CodeDefinition;
use crate::database_types::{DatabaseQuery, GraphIdentifier};

pub const DEFAULT_CLIENT_PORT: u32 = 27615;
pub const DEFAULT_CLIENT_ADDRESS: &str = "127.0.0.1";

pub struct ClientDatabase {
    client: proto::Client,
}

impl DatabaseQuery for ClientDatabase {}

impl ClientDatabase {
    pub async fn new(port: Option<u32>, address: Option<String>) -> Result<Self> {
        let p = port.unwrap_or(DEFAULT_CLIENT_PORT);
        let d = address.unwrap_or(DEFAULT_CLIENT_ADDRESS.to_string());
        let uri = format!("grpc://{}:{}", d, p);
        let client = proto::Client::new(uri.try_into()?).await?;
        Ok(Self { client })
    }

    async fn trace_vertex_name_to_def(&mut self, funcname: &str, def_idt: GraphIdentifier, backward: bool) -> Result<Vec<CodeDefinition>> {
        let mut function_definitions = vec![];

        let vertex_query = Self::trace_helper_get_vertices_query(funcname, backward)?;
        let output = self.client.get(vertex_query).await?;
        let edge_response = indradb::util::extract_edges(output);

        if let Some(edges) = edge_response {
            for edge in edges {
                let vertex_query = Self::trace_helper_get_neighbour_properties_query(&edge, backward)?;
                let output = self.client.get(vertex_query).await?;
                let property_response = indradb::util::extract_vertex_properties(output);

                if let Some(properties) = property_response {
                    let tmp_definitions = Self::collect_matching_idt_definitions(&properties, def_idt)?;
                    function_definitions.extend(tmp_definitions);
                }
            }
        }
        Ok(function_definitions)
    }

    pub async fn get_function_definition_helper(&mut self, funcname: &str, visited: &mut HashSet<String>) -> Result<Vec<CodeDefinition>> {
        let mut ret = vec![];
        let preprocs = self.trace_vertex_name_to_def(funcname, GraphIdentifier::VertexPreprocDefinitionProperty, false).await?;
        let funcs = self.trace_vertex_name_to_def(funcname, GraphIdentifier::VertexFunctionDefinitionProperty, false).await?;
        visited.insert(funcname.to_string());
        ret.extend(funcs);
        for preproc in preprocs.iter() {
            for r in preproc.references.iter() {
                if visited.contains(r) {
                    continue;
                }
                let subcall = Box::pin(self.get_function_definition_helper(&r, visited)).await?;
                ret.extend(subcall);
            }
        }
        ret.extend(preprocs);
        Ok(ret)
    }

    pub async fn get_function_definition(&mut self, funcname: &str) -> Result<Vec<CodeDefinition>> {
        self.get_function_definition_helper(funcname, &mut HashSet::from([])).await
    }

    pub async fn get_function_cross_references(&mut self, funcname: &str) -> Result<Vec<CodeDefinition>> {
        let mut ret = vec![];
        ret.extend(self.trace_vertex_name_to_def(funcname, GraphIdentifier::VertexFunctionDefinitionProperty, true).await?);
        ret.extend(self.trace_vertex_name_to_def(funcname, GraphIdentifier::VertexPreprocDefinitionProperty, true).await?);
        Ok(ret)
    }

    pub async fn get_struct_definition(&mut self, typename: &str) -> Result<Vec<CodeDefinition>> {
        self.trace_vertex_name_to_def(typename, GraphIdentifier::VertexStructDefinitionProperty, false).await
    }

    pub async fn get_enum_definition(&mut self, typename: &str) -> Result<Vec<CodeDefinition>> {
        self.trace_vertex_name_to_def(typename, GraphIdentifier::VertexEnumDefinitionProperty, false).await
    }

    pub async fn get_union_definition(&mut self, typename: &str) -> Result<Vec<CodeDefinition>> {
        self.trace_vertex_name_to_def(typename, GraphIdentifier::VertexUnionDefinitionProperty, false).await
    }

    pub async fn get_typedef_definition(&mut self, typename: &str) -> Result<Vec<CodeDefinition>> {
        self.trace_vertex_name_to_def(typename, GraphIdentifier::VertexTypedefDefinitionProperty, false).await
    }

    pub async fn get_any_type_definition(&mut self, typename: &str) -> Result<Vec<CodeDefinition>> {
        let mut ret = vec![];
        ret.extend(self.get_struct_definition(typename).await?);
        ret.extend(self.get_enum_definition(typename).await?);
        ret.extend(self.get_union_definition(typename).await?);
        ret.extend(self.get_typedef_definition(typename).await?);
        Ok(ret)
    }

}
