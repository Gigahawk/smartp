{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs = {
        pyproject-nix.follows = "pyproject-nix";
        nixpkgs.follows = "nixpkgs";
      };
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs = {
        pyproject-nix.follows = "pyproject-nix";
        uv2nix.follows = "uv2nix";
        nixpkgs.follows = "nixpkgs";
      };
    };

    treefmt-nix = {
      url = "github:numtide/treefmt-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      pyproject-nix,
      uv2nix,
      pyproject-build-systems,
      treefmt-nix,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        inherit (nixpkgs) lib;
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python312;

        workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };
        overlay = workspace.mkPyprojectOverlay {
          sourcePreference = "wheel";
        };
        editableOverlay = workspace.mkEditablePyprojectOverlay {
          root = "$REPO_ROOT";
        };
        hacks = pkgs.callPackage pyproject-nix.build.hacks { };

        pyprojectOverrides = final: prev: {
          pysmart = prev.pysmart.overrideAttrs (old: {
            buildInputs = (old.buildInputs or [ ]) ++ [
              prev.setuptools
              prev.setuptools-scm
              prev.vcs-versioning
            ];
          });
          # Example overrides to fix build
          # psycopg2 = prev.psycopg2.overrideAttrs (old: {
          #   buildInputs = (old.buildInputs or [ ]) ++ [
          #     prev.setuptools
          #     pkgs.libpq.pg_config
          #   ];
          # });
          # casadi = hacks.nixpkgsPrebuild {
          #   from = pkgs.python312Packages.casadi;
          #   prev = prev.casadi;
          # };

          ## TODO: Add tests to package?
          ## Based on https://pyproject-nix.github.io/uv2nix/patterns/testing.html
          ## Doesn't seem to work, smartp package isn't found
          #smartp = prev.smartp.overrideAttrs (old: {
          #  passthru = old.passthru // {
          #    tests =
          #      let
          #        _virtualenv = final.mkVirtualEnv "smartp-pytest-env" workspace.deps.all // {
          #          smartp = [ "dev" ];
          #        };
          #      in
          #      (old.tests or { })
          #      // {
          #        pytest = pkgs.stdenv.mkDerivation {
          #          name = "${final.smartp.name}-pytest";
          #          inherit (final.smartp) src;
          #          nativeBuildInputs = [
          #            virtualenv
          #            _virtualenv
          #          ];
          #          dontConfigure = true;
          #          buildPhase = ''
          #            runHook preBuild
          #            pytest
          #            runHook postBuild
          #          '';
          #        };
          #      };
          #  };
          #});
        };

        pythonSet =
          (pkgs.callPackage pyproject-nix.build.packages {
            inherit python;
          }).overrideScope
            (
              lib.composeManyExtensions [
                pyproject-build-systems.overlays.wheel
                overlay
                pyprojectOverrides
              ]
            );

        editablePythonSet = pythonSet.overrideScope editableOverlay;
        virtualenv = editablePythonSet.mkVirtualEnv "smartp-dev-env" workspace.deps.all;

        inherit (pkgs.callPackages pyproject-nix.build.util { }) mkApplication;

        treefmtEval = treefmt-nix.lib.evalModule pkgs ./treefmt.nix;
      in
      {
        packages = {
          smartp =
            (mkApplication {
              venv = pythonSet.mkVirtualEnv "smartp-app-env" workspace.deps.default;
              package = pythonSet.smartp;
            }).overrideAttrs
              (old: {
                nativeBuildInputs = old.nativeBuildInputs ++ [ pkgs.makeWrapper ];
                postInstall = ''
                  wrapProgram "$out/bin/smartp" \
                      --prefix PATH : ${nixpkgs.lib.makeBinPath [ pkgs.smartmontools ]}
                '';
              });
          default = self.packages.${system}.smartp;
        };
        formatter = treefmtEval.config.build.wrapper;
        checks = {
          formatting = treefmtEval.config.build.check self;
          # Doesn't seem to work
          # pytest = editablePythonSet.smartp.passthru.tests.pytest;
        };
        devShells = {
          default = pkgs.mkShell {
            packages = [
              virtualenv
              pkgs.uv
              pkgs.sphinx
              pkgs.git
            ];
            env = {
              UV_NO_SYNC = "1";
              UV_PYTHON = editablePythonSet.python.interpreter;
              UV_PYTHON_DOWNLOADS = "never";
            }
            // lib.optionalAttrs pkgs.stdenv.isLinux {
              LD_LIBRARY_PATH = lib.makeLibraryPath pkgs.pythonManylinuxPackages.manylinux1;
            };
            shellHook = ''
              unset PYTHONPATH
              export REPO_ROOT=$(git rev-parse --show-toplevel)
              . ${virtualenv}/bin/activate
            '';
          };
        };
      }
    );
}
