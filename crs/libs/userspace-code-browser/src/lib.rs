#[cfg(feature = "pyo3")]
use pyo3::{
    prelude::*,
    exceptions::{PyRuntimeError, PyConnectionRefusedError, PyLookupError, PyValueError},
    wrap_pyfunction,
};
use tokio::runtime::Runtime;

mod types;
mod database_types;
mod client_database;

use client_database::{DEFAULT_CLIENT_PORT, DEFAULT_CLIENT_ADDRESS, ClientDatabase};
use types::definitions_to_string;

#[cfg(feature = "pyo3")]
enum QueryType {
    Function,
    Xref,
    Struct,
    Enum,
    Union,
    Typedef,
    AnyType,
}

#[cfg(feature = "pyo3")]
#[pyclass]
struct CodeBrowser {
    cd: ClientDatabase,
    rt: Runtime,
}

#[cfg(feature = "pyo3")]
#[pymethods]
impl CodeBrowser {
    #[new]
    #[pyo3(signature = (port=None, address=None))]
    fn new(port: Option<u32>, address: Option<String>) -> PyResult<Self> {
        let rt = Runtime::new()
            .map_err(|_| PyRuntimeError::new_err("failed to create async runtime"))?;
        let cd = rt.block_on(ClientDatabase::new(port, address.clone()))
            .map_err(|_| PyConnectionRefusedError::new_err(
                format!(
                    "couldn't connect to {}:{}",
                    address.unwrap_or(DEFAULT_CLIENT_ADDRESS.to_string()),
                    port.unwrap_or(DEFAULT_CLIENT_PORT)
                )
            ))?;
        Ok(Self { cd, rt })
    }

    fn get_function_definition(&mut self, name: String, json: bool) -> PyResult<String> {
        let future = self.cd.get_function_definition(&name);
        let defs = self.rt.block_on(future)
            .map_err(|e| PyLookupError::new_err(e.to_string()))?;
        let ret = definitions_to_string(defs, json)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(ret)
    }

    fn get_function_cross_references(&mut self, name: String, json: bool) -> PyResult<String> {
        let future = self.cd.get_function_cross_references(&name);
        let defs = self.rt.block_on(future)
            .map_err(|e| PyLookupError::new_err(e.to_string()))?;
        let ret = definitions_to_string(defs, json)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(ret)
    }

    fn get_struct_definition(&mut self, name: String, json: bool) -> PyResult<String> {
        let future = self.cd.get_struct_definition(&name);
        let defs = self.rt.block_on(future)
            .map_err(|e| PyLookupError::new_err(e.to_string()))?;
        let ret = definitions_to_string(defs, json)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(ret)
    }

    fn get_enum_definition(&mut self, name: String, json: bool) -> PyResult<String> {
        let future = self.cd.get_enum_definition(&name);
        let defs = self.rt.block_on(future)
            .map_err(|e| PyLookupError::new_err(e.to_string()))?;
        let ret = definitions_to_string(defs, json)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(ret)
    }

    fn get_union_definition(&mut self, name: String, json: bool) -> PyResult<String> {
        let future = self.cd.get_union_definition(&name);
        let defs = self.rt.block_on(future)
            .map_err(|e| PyLookupError::new_err(e.to_string()))?;
        let ret = definitions_to_string(defs, json)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(ret)
    }

    fn get_typedef_definition(&mut self, name: String, json: bool) -> PyResult<String> {
        let future = self.cd.get_typedef_definition(&name);
        let defs = self.rt.block_on(future)
            .map_err(|e| PyLookupError::new_err(e.to_string()))?;
        let ret = definitions_to_string(defs, json)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(ret)
    }

    fn get_any_type_definition(&mut self, name: String, json: bool) -> PyResult<String> {
        let future = self.cd.get_any_type_definition(&name);
        let defs = self.rt.block_on(future)
            .map_err(|e| PyLookupError::new_err(e.to_string()))?;
        let ret = definitions_to_string(defs, json)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(ret)
    }
}

#[cfg(feature = "pyo3")]
async fn async_get_definition(qt: QueryType, name: String, json: bool, port: Option<u32>, address: Option<String>) -> PyResult<String> {
    let mut client = ClientDatabase::new(port, address.clone()).await
        .map_err(|_| PyConnectionRefusedError::new_err(
            format!(
                "couldn't connect to {}:{}",
                address.unwrap_or(DEFAULT_CLIENT_ADDRESS.to_string()),
                port.unwrap_or(DEFAULT_CLIENT_PORT)
            )
        ))?;

    let defs = match qt {
        QueryType::Function => client.get_function_definition(&name).await,
        QueryType::Xref => client.get_function_cross_references(&name).await,
        QueryType::Struct => client.get_struct_definition(&name).await,
        QueryType::Enum => client.get_enum_definition(&name).await,
        QueryType::Union => client.get_union_definition(&name).await,
        QueryType::Typedef => client.get_typedef_definition(&name).await,
        QueryType::AnyType => client.get_any_type_definition(&name).await,
    }.map_err(|e| PyLookupError::new_err(e.to_string()))?;

    let ret = definitions_to_string(defs, json)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    Ok(ret)
}

#[cfg(feature = "pyo3")]
fn get_definition(qt: QueryType, name: String, json: bool, port: Option<u32>, address: Option<String>) -> PyResult<String> {
    let rt = Runtime::new()
        .map_err(|_| PyRuntimeError::new_err("failed to create async runtime"))?;
    rt.block_on(async_get_definition(qt, name, json, port, address))
}

#[cfg(feature = "pyo3")]
#[pyfunction]
#[pyo3(signature = (name, json, port=None, address=None))]
pub fn get_function_definition(name: String, json: bool, port: Option<u32>, address: Option<String>) -> PyResult<String> {
    get_definition(QueryType::Function, name, json, port, address)
}

#[cfg(feature = "pyo3")]
#[pyfunction]
#[pyo3(signature = (name, json, port=None, address=None))]
pub fn get_function_cross_references(name: String, json: bool, port: Option<u32>, address: Option<String>) -> PyResult<String> {
    get_definition(QueryType::Xref, name, json, port, address)
}

#[cfg(feature = "pyo3")]
#[pyfunction]
#[pyo3(signature = (name, json, port=None, address=None))]
pub fn get_struct_definition(name: String, json: bool, port: Option<u32>, address: Option<String>) -> PyResult<String> {
    get_definition(QueryType::Struct, name, json, port, address)
}

#[cfg(feature = "pyo3")]
#[pyfunction]
#[pyo3(signature = (name, json, port=None, address=None))]
pub fn get_enum_definition(name: String, json: bool, port: Option<u32>, address: Option<String>) -> PyResult<String> {
    get_definition(QueryType::Enum, name, json, port, address)
}

#[cfg(feature = "pyo3")]
#[pyfunction]
#[pyo3(signature = (name, json, port=None, address=None))]
pub fn get_union_definition(name: String, json: bool, port: Option<u32>, address: Option<String>) -> PyResult<String> {
    get_definition(QueryType::Union, name, json, port, address)
}

#[cfg(feature = "pyo3")]
#[pyfunction]
#[pyo3(signature = (name, json, port=None, address=None))]
pub fn get_typedef_definition(name: String, json: bool, port: Option<u32>, address: Option<String>) -> PyResult<String> {
    get_definition(QueryType::Typedef, name, json, port, address)
}

#[cfg(feature = "pyo3")]
#[pyfunction]
#[pyo3(signature = (name, json, port=None, address=None))]
pub fn get_any_type_definition(name: String, json: bool, port: Option<u32>, address: Option<String>) -> PyResult<String> {
    get_definition(QueryType::AnyType, name, json, port, address)
}

#[cfg(feature = "pyo3")]
#[pymodule]
fn userspace_code_browser(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get_function_definition, m)?)?;
    m.add_function(wrap_pyfunction!(get_function_cross_references, m)?)?;
    m.add_function(wrap_pyfunction!(get_struct_definition, m)?)?;
    m.add_function(wrap_pyfunction!(get_enum_definition, m)?)?;
    m.add_function(wrap_pyfunction!(get_union_definition, m)?)?;
    m.add_function(wrap_pyfunction!(get_typedef_definition, m)?)?;
    m.add_function(wrap_pyfunction!(get_any_type_definition, m)?)?;
    m.add_class::<CodeBrowser>()?;
    Ok(())
}
