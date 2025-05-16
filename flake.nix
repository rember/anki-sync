{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    # Using an older nixpkgs commit that still includes Python 3.9
    nixpkgs-py39.url = "github:NixOS/nixpkgs/43aad2d1454023a3cf6a06f80a5cf70f95d6ffcf";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    nixpkgs,
    nixpkgs-py39,
    flake-utils,
    ...
  }: flake-utils.lib.eachDefaultSystem(system:
    let
      pkgs = import nixpkgs {
        inherit system;
      };
      pkgs-py39 = import nixpkgs-py39 {
        inherit system;
      };
    in
    with pkgs;
    {
      devShells.default = mkShell {
        buildInputs = [
          pkgs-py39.python39
          uv
        ];
      };
    }
  );
}
