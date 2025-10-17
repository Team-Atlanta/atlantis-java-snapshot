use serde::{Serialize, Deserialize};
use serde_json;
use anyhow::Result;

#[derive(Debug, Serialize, Deserialize, PartialEq, Clone, Copy)]
pub enum CodeDefinitionType {
    Function,
    Struct,
    Enum,
    Union,
    Typedef,
    Preproc,
}

/// Function definition parsed from C source
#[derive(Debug, Serialize, Deserialize, PartialEq, Clone)]
pub struct CodeDefinition {
    pub name: String,
    pub definition: String,
    pub filename: String,
    pub references: Vec<String>,
    pub def_type: CodeDefinitionType,
}

#[allow(dead_code)]
#[derive(Default)]
pub struct CodeDefinitionBuilder {
    name: Option<String>,
    definition: Option<String>,
    filename: Option<String>,
    references: Option<Vec<String>>,
    pub def_type: Option<CodeDefinitionType>,
}

#[allow(dead_code)]
impl CodeDefinitionBuilder {
    pub fn set_name(&mut self, name: String) {
        self.name = Some(name);
    }

    pub fn set_definition(&mut self, definition: String) {
        self.definition = Some(definition);
    }

    pub fn set_filename(&mut self, filename: String) {
        self.filename = Some(filename);
    }

    pub fn set_references(&mut self, references: Vec<String>) {
        self.references = Some(references);
    }

    pub fn set_type(&mut self, def_type: CodeDefinitionType) {
        self.def_type = Some(def_type);
    }

    pub fn is_ready(&self) -> bool {
        self.name.is_some()
            && self.definition.is_some()
            && self.filename.is_some()
            && self.references.is_some()
            && self.def_type.is_some()
    }
    
    pub fn build(self) -> Option<CodeDefinition> {
        Some(CodeDefinition {
            name: self.name?,
            definition: self.definition?,
            filename: self.filename?,
            references: self.references?,
            def_type: self.def_type?,
        })
    }
}

pub fn definitions_to_string(defs: Vec<CodeDefinition>, json: bool) -> Result<String> {
    let mut ret = "".to_string();
    if json {
        ret = format!("{}\n", serde_json::to_string(&defs)?);
    }
    else {
        for def in defs {
            let line = format!("{}\n{}\n", def.filename, def.definition);
            ret.push_str(&line);
        }
    }
    Ok(ret)
}

#[allow(dead_code)]
pub fn print_definitions(defs: Vec<CodeDefinition>, json: bool) -> Result<()> {
    println!("{}", definitions_to_string(defs, json)?);
    Ok(())
}
