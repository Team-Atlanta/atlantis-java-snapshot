{
  description = "bear";

  inputs =
    {
      flake-utils.url = "github:numtide/flake-utils";
      nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
      # nixpkgs-bear.url = "github:nixos/nixpkgs/22f65339f3773f5b691f55b8b3a139e5582ae85b"; # 2.3.13
      nixpkgs-bear.url = "github:nixos/nixpkgs/1b42ce6bead608458d8a9edc45c3f5f242e620f3"; # 2.4.2, seems to work
      # nixpkgs-bear.url = "github:nixos/nixpkgs/903b8cc6f2045eadb0d7e58913447b0467a5d8a3"; # 3.0.9, segfaults
      # nixpkgs-bear.url = "github:nixos/nixpkgs/b0f0b5c6c021ebafbd322899aa9a54b87d75a313"; # 3.0.12, segfaults
    };

  outputs = { self, nixpkgs, nixpkgs-bear, flake-utils, ... }@inputs:
    flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs = nixpkgs.legacyPackages.${system};
      pkgs-bear = nixpkgs-bear.legacyPackages.${system};
    in
    {
      devShells.default =
        pkgs.mkShell
          {
            nativeBuildInputs = [
              pkgs-bear.bear
              pkgs.fd
              pkgs.python3
              (pkgs.python3.withPackages (p: with p; [
                pyyaml
              ]))
            ];
          };
    });
}

