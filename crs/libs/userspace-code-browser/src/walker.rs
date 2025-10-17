use walkdir::WalkDir;

fn is_suffix_file(name: &str, suffices: &[&str]) -> bool {
    for suffix in suffices {
        if name.ends_with(suffix) { return true; }
    }
    false
}

fn is_c_file(name: &str) -> bool {
    is_suffix_file(name, &[".c", ".h", ".cc", ".hh", ".cpp", ".cxx", ".C"])
}

pub fn get_all_c_paths(root_path: &str) -> Vec<String> {
    let mut all_c_paths = vec![];
    // DEBUG take(50).
    for entry in WalkDir::new(root_path).into_iter().filter_map(|e| e.ok()) {
        let canonical_path  = entry.path().canonicalize();
        if canonical_path.is_err() { continue; }
        let canonical_path = canonical_path.unwrap();
        let canonical_path_str = canonical_path.to_str();
        if canonical_path_str.is_none() { continue; }
        let canonical_path_str = canonical_path_str.unwrap();
        if is_c_file(canonical_path_str) {
            all_c_paths.push(canonical_path_str.to_string());
        }
    }
    all_c_paths
}
