# Phase 3D Colab Verification

PARTIALLY COMPLETE: executable workflow implemented and locally validated.

{
  "status": "partially_complete_colab_execution_outstanding",
  "platform": "Windows-11-10.0.26100-SP0",
  "python": "3.12.10",
  "research_tests": 177,
  "research_passed": true,
  "research_skipped": 0,
  "backend_tests": 104,
  "backend_passed": true,
  "research_log": ".................................................................................................................................................................................\n----------------------------------------------------------------------\nRan 177 tests in 26.017s\n\nOK\n",
  "backend_log": "........................................................................................................\n----------------------------------------------------------------------\nRan 104 tests in 1.211s\n\nOK\n",
  "compilation": "passed",
  "notebook_json_and_code": "passed",
  "shell_syntax": "bash -n passed in setup tests",
  "historical": {
    "sealed_phases": {
      "phase_3d_hashes_verified": 26,
      "historical": {
        "phase_3c_hashes_verified": 30,
        "historical": {
          "phase_3b_output_hashes_verified": 52,
          "historical": {
            "manifest_revision": 2,
            "phase_3_output_hashes_verified": 51,
            "prior_output_hashes_verified": 44
          }
        }
      }
    },
    "recovery_outputs_verified": 9
  },
  "historical_routing": {
    "logical_pairs": 30000,
    "physical_keys": 30000,
    "statuses": {
      "valid": 0,
      "unreachable": 0,
      "missing": 30000,
      "temporary_provider_failure": 0,
      "invalid_request": 0,
      "unverified_response": 0
    },
    "missing_logical_pairs": 30000,
    "complete": false
  },
  "source_files": {
    "notebooks/DhakaNest_Phase3D_Colab_OSRM.ipynb": "f149b17a28b26b5a869e708d42fc486e9f10ff5c338c0ab24e46dd2753ae0be5",
    "routing/osrm_colab/.gitignore": "fd98bc584b76d28f4848c9ae6f8881404a151dc4d585df0e1cf106260f8476cc",
    "routing/osrm_colab/__init__.py": "1b36a1526cbbb9429c129dbf86ace7b5521dc469a9c75468b32bf1767157b671",
    "routing/osrm_colab/audit_python_compatibility.py": "2a6b16fe760529eb03effd88d478c625610bf9fbd55f931aadb4507ff98963b8",
    "routing/osrm_colab/colab_config.example.json": "1c4cf348a1530c7b6522a33a6b95b7903a77cc81aeac2d9656b9de82612e9da2",
    "routing/osrm_colab/environment-spec-v2.json": "80bb1216e29c6c3c87f381d1bba1a4f7692a1f98e0f4ab9472d48a367097f408",
    "routing/osrm_colab/environment.py": "c1d3e3feb4d1548a4c745f055fcfbffcfadbc7cedf5c8f519d68639347124e6c",
    "routing/osrm_colab/install_dependencies.sh": "7cd33e2f3b5aa062f028580e35e5d593e61704b1bc27615f4ede2c00586bd3a5",
    "routing/osrm_colab/notebook.py": "df452e45f354b2669e361eadb1e93779524d28026c700b3dc9e7e272a9ef5047",
    "routing/osrm_colab/notebook_compat.py": "ff62e0957c896b9ac3bf857bf800400de4346c0879d4e52709a1c8ca0088cf33",
    "routing/osrm_colab/preprocess_osm.sh": "e3ab5ed3989cab0c0e18ff39f000c1f4305abae7ce69e2e60852763da6d24f1e",
    "routing/osrm_colab/README.md": "fac987e620215b46c11beee24961a8cbc7cad7279f9178bfd9027504f25b1ef2",
    "routing/osrm_colab/report.py": "7a9d3942d3018f0c91b315e6a4baba06ce774e55012950770994d4743ba7ea49",
    "routing/osrm_colab/requirements-colab-py313-v1.lock.txt": "19ab66d3f5b609cd1324e071d7fa8eb962d933f776574fd614b5afe8232cf435",
    "routing/osrm_colab/requirements-colab-py313-v1.txt": "d3802e11e8d344590f0265846cc688f7a7b39f4ee77261b21d2f8a586d3f43fc",
    "routing/osrm_colab/requirements-colab.txt": "7d3a6901baa7feaf3d2e42b3366d14aa0784b0ffd02f1c15a1435fa75c5849e7",
    "routing/osrm_colab/setup_osrm.sh": "b0be9ee39ec180073da895cd6994d71e8bb0d5ce98396c22b84e805fe93a55df",
    "routing/osrm_colab/start_osrm.sh": "84fe2e61972497757fc1bff7004c24bbe7d9a25dba6fd170498bd49656fd73d8",
    "routing/osrm_colab/storage.py": "ac83e26d46d1c11220c51d0b9dbfe73d1c31b03ffe49af9f72d1b3b948eb8074",
    "routing/osrm_colab/verify.py": "0069912131d7c8141d637d7b808ef6d3ea7f2bb921e5ceb25261e6c8585a2f47",
    "routing/osrm_colab/verify_osrm.py": "8c353c99ea6954c766af722044915e71e5d7a891a05c4977d616b35944b69dab",
    "routing/osrm_colab/workflow.py": "ac0d8fb63ab35e439d00478e3c0b2e937bd315957d27a23055911569a251bf3c",
    "tests/test_colab_checkpointing.py": "c7d55385f9e10cc72549c2c10e1fc019f6a2658f16a72e1abc09b96c37b4ccff",
    "tests/test_colab_python_compatibility.py": "f808aa2b1a0ca20bf7249a528bc14d9512674d2afcf2003e3068bcc91dda2540",
    "tests/test_colab_routing.py": "6cd1dbb28bac57283fd5cec935726e73efb66fdbb438dd9aab7e26092f704b74",
    "tests/test_colab_setup.py": "ee76acebe63ac7276e78d6839f4c4c2d90727f9838d4109307a538c94796935f"
  },
  "production_diff": "empty",
  "git_status": "?? research/\n",
  "database_access": false,
  "colab_executed": false,
  "downloads": 0,
  "preprocessing_executed": false,
  "live_route_requests": 0,
  "new_measured_pairs": 0,
  "new_verified_unreachable_pairs": 0,
  "commute_feasible_distribution": null,
  "final_annotation_pool_size": null,
  "offline_routing_benchmark_ready": false,
  "phase4_ready": false
}

Historical route evidence remains 0 valid, 0 unreachable, 30,000 missing. Final candidate distribution and pool size remain unknown. Phase 4 is not ready or authorized.
