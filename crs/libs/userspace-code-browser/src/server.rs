use std::collections::HashMap;
use std::sync::Arc;
use std::env;
use std::path::Path;
use std::fs::{create_dir_all, remove_dir_all, File};
use tonic::{transport::Server, Request, Response, Status};
use tokio::{self, sync::Mutex};
use indradb;
use clap::Parser;
use anyhow::{anyhow, Result};
use flate2::read::GzDecoder;
use tar::Archive;

mod code_browser_proto {
    tonic::include_proto!("codebrowser");
}
mod queries;
mod database_types;
mod disk_database;
mod types;
mod builder;
mod tree_sitter_helper;
mod walker;

use code_browser_proto::code_browser_server::{CodeBrowser, CodeBrowserServer};
use code_browser_proto::{CodeRequest, CodeResponse, BuildRequest, BuildResponse};
use code_browser_proto::CodeDefinition as ProtoCodeDefinition;
use disk_database::{GenericDatabase, MemoryDatabase};
use types::{CodeDefinition, CodeDefinitionType};

#[derive(Parser)]
#[command(name = "code-browser-server")]
struct Args {
    /// Path to source code
    #[clap(short, long)]
    path: Option<String>,

    /// gRPC address and port
    #[clap(short, long, default_value = "[::1]:50051")]
    address: String,

    /// Shared directory
    #[clap(short, long, default_value = "/shared-crs-fs/crs-userspace/code-browser")]
    shared: String,
}

impl From<ProtoCodeDefinition> for CodeDefinition {
    fn from(proto: ProtoCodeDefinition) -> Self {
        CodeDefinition {
            name: proto.name,
            definition: proto.definition,
            filename: proto.filename,
            references: proto.references,
            def_type: proto.def_type.into(),
        }
    }
}

impl From<CodeDefinition> for ProtoCodeDefinition {
    fn from(def: CodeDefinition) -> Self {
        ProtoCodeDefinition {
            name: def.name,
            definition: def.definition,
            filename: def.filename,
            references: def.references,
            def_type: def.def_type.into(),
        }
    }
}

impl From<i32> for CodeDefinitionType {
    fn from(proto: i32) -> Self {
        match proto {
            0 => CodeDefinitionType::Function,
            1 => CodeDefinitionType::Struct,
            2 => CodeDefinitionType::Enum,
            3 => CodeDefinitionType::Union,
            4 => CodeDefinitionType::Typedef,
            5 => CodeDefinitionType::Preproc,
            _ => CodeDefinitionType::Function, // shouldn't happen
        }
    }
}

impl From<CodeDefinitionType> for i32 {
    fn from(def: CodeDefinitionType) -> Self {
        match def {
            CodeDefinitionType::Function => 0,
            CodeDefinitionType::Struct => 1,
            CodeDefinitionType::Enum => 2,
            CodeDefinitionType::Union => 3,
            CodeDefinitionType::Typedef => 4,
            CodeDefinitionType::Preproc => 5,
        }
    }
}

pub struct CodeBrowserService<T: indradb::Datastore> {
    // db: GenericDatabase<T>,
    default: Option<String>,
    project_map: Mutex<HashMap<String, Arc<GenericDatabase<T>>>>,
    shared_dir: String,
}

impl CodeBrowserService<indradb::MemoryDatastore> {
    pub fn new(shared_dir: String) -> Self {
        let project_map = HashMap::new();
        Self {
            default: None,
            project_map: Mutex::new(project_map),
            shared_dir,
        }
    }

    pub fn with_default(shared_dir: String, default: String) -> Self {
        let db = MemoryDatabase::new();
        builder::main_build(&db, &default);
        let project_map = HashMap::from([
            (default.clone(), Arc::new(db)),
        ]);
        Self {
            default: Some(default),
            project_map: Mutex::new(project_map),
            shared_dir,
        }
    }

    pub async fn build(&self, project: String, force: bool, tarball: String) -> Result<()> {
        let mut project_map = self.project_map.lock().await;
        if !force && project_map.contains_key(&project) {
            return Ok(());
        }
        let db = MemoryDatabase::new();

        let tarball_base = Path::new(&tarball).file_stem().and_then(|s| s.to_str()).unwrap_or(&tarball);
        let project_path = env::temp_dir().join(tarball_base);
        let tarball_path = Path::new(&self.shared_dir).join(&tarball);

        // if project_path exists, return
        if !force && project_path.exists() {
            return Ok(());
        }

        // if project_path exists, remove it
        if project_path.exists() {
            remove_dir_all(&project_path)?;
        }
        create_dir_all(&project_path)?;

        // extract tarball
        let tar_gz = File::open(tarball_path)?;
        let tar = GzDecoder::new(tar_gz);
        let mut archive = Archive::new(tar);
        archive.unpack(&project_path)?;

        // get directory inside project_path if only one, otherwise just project_path   
        let project_dir = if let Ok(mut entries) = project_path.read_dir() {
            let entry = entries.next();
            if entry.is_some() && entries.next().is_none() {
                entry.unwrap()?.path()
            } else { project_path }
        } else { project_path };

        builder::main_build(&db, project_dir.to_str().ok_or(anyhow!("invalid project_dir string"))?);
        project_map.insert(project, Arc::new(db));
        Ok(())
    }

    pub async fn get_db(&self, project: &str) -> Option<Arc<MemoryDatabase>> {
        let project_map = self.project_map.lock().await;
        project_map.get(project).cloned()
    }

    pub async fn get_default(&self) -> Option<Arc<MemoryDatabase>> {
        if self.default.is_none() {
            return None;
        }
        let key = self.default.as_deref().unwrap();
        self.get_db(key).await
    }
}


#[tonic::async_trait]
impl CodeBrowser for CodeBrowserService<indradb::MemoryDatastore> {
    async fn code_query(&self, request: Request<CodeRequest>) -> Result<Response<CodeResponse>, Status> {
        let req = request.into_inner();

        let (db_res, project) = if let Some(project) = req.project {
            (self.get_db(&project).await, project.clone())
        }
        else {
            (self.get_default().await, self.default.clone().unwrap_or_default())
        };
        if db_res.is_none() {
            return Ok(Response::new(CodeResponse {
                error: "Could not find corresponding database".to_string(),
                definitions: vec![],
            }));
        }
        let db = db_res.unwrap();

        // TODO test panics?
        let result = match req.kind {
            0 => db.get_function_definition(&req.name),
            1 => db.get_function_cross_references(&req.name),
            2 => db.get_struct_definition(&req.name),
            3 => db.get_enum_definition(&req.name),
            4 => db.get_union_definition(&req.name),
            5 => db.get_typedef_definition(&req.name),
            6 => db.get_any_type_definition(&req.name),
            _ => Err(anyhow!("Unsupported request query kind")),
        };

        let response = match result {
            Ok(code_definitions) => {
                let code_definitions = if !req.relative {
                    code_definitions.into_iter().map(|mut code_definition| {
                        let full_path = Path::new(&project).join(&code_definition.filename);
                        code_definition.filename = full_path.to_string_lossy().into_owned();
                        code_definition
                    }).collect()
                } else { code_definitions };
                let definitions = code_definitions.into_iter().map(|e| e.into()).collect();
                CodeResponse { error: "".to_string(), definitions }
            }
            Err(e) => {
                CodeResponse { error: format!("Code Browser Server Error: {}", e), definitions: vec![] }
            }
        };
        
        Ok(Response::new(response))
    }

    async fn build(&self, request: Request<BuildRequest>) -> Result<Response<BuildResponse>, Status> {
        let req = request.into_inner();
        let res = self.build(req.project.to_string(), req.force, req.tarball).await;
        match res {
            Ok(_) => Ok(Response::new(BuildResponse { error: "".to_string() })),
            Err(e) => Ok(Response::new(BuildResponse { error: format!("Code Browser Server Error: {}", e) })),
        }
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();

    let addr = args.address.parse()?;
    let shared_dir = args.shared;
    let service = if args.path.is_some() {
        CodeBrowserService::with_default(shared_dir, args.path.unwrap())
    }
    else {
        CodeBrowserService::new(shared_dir)
    };

    // let service = CodeBrowserService::new(db);

    println!("Starting server on {}", addr);
    
    Server::builder()
        .add_service(CodeBrowserServer::new(service))
        .serve(addr)
        .await?;

    Ok(())
}
