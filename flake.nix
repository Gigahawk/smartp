{
  description = "Application packaged using poetry2nix";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        # see https://github.com/nix-community/poetry2nix/tree/master#api for more functions and examples.
        pkgs = nixpkgs.legacyPackages.${system};
        inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryApplication;
      in
      {
        packages = {
          smartp = mkPoetryApplication {
            projectDir = self;
            nativeBuildInputs = [ pkgs.makeWrapper ];
            propogatedBuildInputs = [
              pkgs.smartmontools
              pkgs.util-linux
              ];
            postInstall = ''
              wrapProgram "$out/bin/smartp" \
                --prefix PATH : ${
                  nixpkgs.lib.makeBinPath [
                    pkgs.smartmontools
                    pkgs.util-linux
                  ]}
            '';
          };
          default = self.packages.${system}.smartp;
        };

        devShells.default = pkgs.mkShell {
          inputsFrom = [ self.packages.${system}.smartp ];
          packages = [
            pkgs.poetry
            ];
        };
      });
}
