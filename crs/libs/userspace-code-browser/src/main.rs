use std::process::ExitCode;
use clap::{Parser, Subcommand, ValueEnum, ValueHint};
use anyhow::{Result, bail};
use std::path::Path;
use tokio::runtime::Runtime;

mod queries;
mod database_types;
mod disk_database;
mod client_database;
mod types;
mod builder;
mod tree_sitter_helper;
mod conditional;
mod walker;

use disk_database::{DiskDatabase, DEFAULT_DB_LOCATION};
use client_database::ClientDatabase;

// NOTE test on vlc/src/audio_output/
// NOTE the macro in VLC foreach_es_then_es_slaves(es) isn't a function definition! It's for loop.
// NOTE keywords at https://github.com/tree-sitter/tree-sitter-c/blob/master/src/node-types.json

#[derive(Parser)]
#[command(name = "code-browser")]
struct Args {
    #[command(subcommand)]
    command: Commands,

    /// Path to desired database storage. Defaults to "./project_db/"
    #[arg(short, long)]
    database: Option<String>,

    /// Output function definitions in JSON format
    #[arg(short, long)]
    json: bool,

    /// Enable client mode
    #[arg(short, long)]
    client: bool,

    /// Client mode: optionally specify a port and address
    #[clap(short, long, num_args(1..=2), value_delimiter = ',', value_hint = ValueHint::Other)]
    grpc: Vec<String>,

    /// Verbose, mainly to check error message
    #[arg(short, long)]
    verbose: bool,
}

#[derive(Subcommand)]
enum Commands {
    /// Construct a database for quick lookup
    Build {
        /// Path to source code
        path: String,
    },

    /// Get function definition
    Definition {
        function: String,
    },

    /// Get cross references for specific function
    Xref {
        function: String,
    },

    /// Get a conditional block given a file and line number
    Conditional {
        // TODO include column?
        /// Path to single source code file
        path: String,
        /// Line number, starting at 1
        line: usize,
    },

    /// Get type definition
    Type {
        /// What kind of type to query. Defaults to all.
        #[arg(short, long, value_enum)]
        kind: Option<TypeKind>,
        /// Name of type to query
        type_: String,
    },
}

#[derive(Clone, ValueEnum)]
enum TypeKind {
    All,
    Struct,
    Enum,
    Union,
    Typedef,
}

async fn main_client_query(args: Args, port: Option<u32>, address: Option<String>) -> Result<()> {
    let mut client = ClientDatabase::new(port, address).await?;
    match args.command {
        Commands::Definition { function } => {
            let defs = client.get_function_definition(&function).await?;
            types::print_definitions(defs, args.json)?;
        }
        Commands::Xref { function } => {
            let defs = client.get_function_cross_references(&function).await?;
            types::print_definitions(defs, args.json)?;
        }
        Commands::Type { kind, type_ } => {
            let defs = match kind {
                Some(TypeKind::Struct) => client.get_struct_definition(&type_).await?,
                Some(TypeKind::Enum) => client.get_enum_definition(&type_).await?,
                Some(TypeKind::Union) => client.get_union_definition(&type_).await?,
                Some(TypeKind::Typedef) => client.get_typedef_definition(&type_).await?,
                Some(TypeKind::All) | None => client.get_any_type_definition(&type_).await?,
            };
            types::print_definitions(defs, args.json)?;
        }
        _ => {
            bail!("Unsupported command in client mode");
        }
    }
    Ok(())
}

fn main_wrapper(args: Args) -> Result<()> {
    if let Commands::Conditional { path, line } = args.command {
        let block = conditional::get_conditional(&path, line)?;
        println!("{}", block);
        return Ok(());
    }

    if args.client {
        let (port, addr) = match args.grpc.as_slice() {
            [] => (None, None),
            [port] => (port.parse::<u32>().ok(), None),
            [port, addr] => (port.parse::<u32>().ok(), Some(addr.clone())),
            _ => (None, None), // Should never be hit due to num_args(0..=2)
        };
        let rt = Runtime::new()?;
        rt.block_on(main_client_query(args, port, addr))?;
        return Ok(());
    }

    let location = args.database.unwrap_or(DEFAULT_DB_LOCATION.to_string());
    let db_path = Path::new(&location);
    let db_parent_path = db_path.parent();
    if db_parent_path.is_none() {
        bail!("Couldn't get parent of database path");
    }

    let db = DiskDatabase::new(db_path);
    match args.command {
        Commands::Build { path } => {
            builder::main_build(&db, &path);
        }
        Commands::Definition { function } => {
            let defs = db.get_function_definition(&function)?;
            types::print_definitions(defs, args.json)?;
            drop(db);
        }
        Commands::Xref { function } => {
            let defs = db.get_function_cross_references(&function)?;
            types::print_definitions(defs, args.json)?;
            drop(db);
        }
        Commands::Type { kind, type_ } => {
            let defs = match kind {
                Some(TypeKind::Struct) => db.get_struct_definition(&type_)?,
                Some(TypeKind::Enum) => db.get_enum_definition(&type_)?,
                Some(TypeKind::Union) => db.get_union_definition(&type_)?,
                Some(TypeKind::Typedef) => db.get_typedef_definition(&type_)?,
                Some(TypeKind::All) | None => db.get_any_type_definition(&type_)?,
            };
            types::print_definitions(defs, args.json)?;
            drop(db);
        }
        _ => {}
    }
    Ok(())
}

fn main() -> ExitCode {
    let args = Args::parse();
    let verbose = args.verbose;
    let main_res = main_wrapper(args);
    if let Err(main_err) = main_res {
        if verbose {
            eprintln!("{}", main_err);
        }
        return ExitCode::FAILURE;
    }
    ExitCode::SUCCESS
}
