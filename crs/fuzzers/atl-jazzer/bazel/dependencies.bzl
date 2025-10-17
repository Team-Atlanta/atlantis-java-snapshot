# Copyright 2025 Code Intelligence GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Common dependencies for the Jazzer project."""

# Dependencies required by soot
SOOT_DEPS = [
    "@maven//:ca_mcgill_sable_jasmin",
    "@maven//:ca_mcgill_sable_polyglot",
    "@maven//:com_google_android_android",
    "@maven//:com_google_guava_guava",
    "@maven//:com_google_protobuf_protobuf_java",
    "@maven//:commons_io_commons_io",
    "@maven//:de_upb_cs_swt_axml",
    "@maven//:de_upb_cs_swt_heros",
    "@maven//:jakarta_annotation_jakarta_annotation_api",
    "@maven//:jakarta_xml_bind_jakarta_xml_bind_api",
    "@maven//:org_apache_ant_ant",
    "@maven//:org_glassfish_jaxb_jaxb_runtime",
    "@maven//:org_hamcrest_hamcrest_all",
    "@maven//:org_javassist_javassist",
    "@maven//:org_slf4j_slf4j_api",
    "@maven//:org_slf4j_slf4j_simple",
    "@maven//:org_smali_dexlib2",
    "@maven//:xmlpull_xmlpull",
    "@org_ow2_asm_asm//jar",
    "@org_ow2_asm_asm_commons//jar",
    "@org_ow2_asm_asm_tree//jar",
    "@org_ow2_asm_asm_util//jar",
    "@org_soot-oss_soot//jar",
]
