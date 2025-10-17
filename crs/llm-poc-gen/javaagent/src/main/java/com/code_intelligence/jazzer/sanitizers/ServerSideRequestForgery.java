/*
 * Copyright 2024 Code Intelligence GmbH
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.code_intelligence.jazzer.sanitizers;


import java.util.concurrent.atomic.AtomicReference;
import java.util.function.BiPredicate;

public class ServerSideRequestForgery {
  // Set via reflection by Jazzer's BugDetectors API.
   // Allow connections to all hosts and ports until before a fuzz target is executed for the first
   // time. This allows the fuzzing setup to connect anywhere without triggering an SSRF-finding
   // during initialization.
  public static final AtomicReference<BiPredicate<String, Integer>> connectionPermitted =
    new AtomicReference<>((host, port) -> true);
}
