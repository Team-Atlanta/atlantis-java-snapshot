/*
 * Copyright 2025 Code Intelligence GmbH
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.example;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import javax.xml.xpath.XPathFactory;
import org.xml.sax.InputSource;

/**
 * A fuzz target that calls various sinkpoint methods with different hook types. This tests
 * CodeMarkerInstrumentor with different HookInstrumentor hook types.
 */
public class CodeMarkerFuzzTarget {

  public static void fuzzerTestOneInput(byte[] input) {
    if (input.length == 0) return;

    // Test with HookType.REPLACE (XPath.evaluate)
    testXPathEvaluate(new String(input, StandardCharsets.UTF_8));

    // Test with HookType.BEFORE/AFTER (ObjectInputStream.readObject)
    testDeserialization(input);

    // Test with custom API sinkpoint
    testCustomAPI(input);
  }

  // Tests CodeMarkerInstrumentor with HookType.REPLACE hook
  private static void testXPathEvaluate(String input) {
    try {
      XPathFactory.newInstance()
          .newXPath()
          .evaluate(input, new InputSource(new StringReader("<root/>")));
    } catch (Exception e) {
      // Ignore exceptions
    }
  }

  // Tests CodeMarkerInstrumentor with HookType.BEFORE/AFTER hooks
  private static void testDeserialization(byte[] unused) {
    try {
      // Create valid serialized data
      ByteArrayOutputStream baos = new ByteArrayOutputStream();
      ObjectOutputStream oos = new ObjectOutputStream(baos);
      oos.writeObject("Test String");
      byte[] data = baos.toByteArray();
      oos.close();

      // Deserialize (triggers CodeMarkerInstrumentor and HookInstrumentor)
      ByteArrayInputStream bais = new ByteArrayInputStream(data);
      ObjectInputStream ois = new ObjectInputStream(bais);
      ois.readObject();
      ois.close();
    } catch (Exception e) {
      // Ignore exceptions
    }
  }

  // Tests custom API sinkpoint via configuration
  private static void testCustomAPI(byte[] input) {
    try {
      // This method itself should be detected as a sinkpoint when
      // ATLJAZZER_CUSTOM_SINKPOINT_CONF env variable is set
      String value = new String(input, StandardCharsets.UTF_8);
      System.out.println(
          "Processing input in custom API: " + value.substring(0, Math.min(value.length(), 10)));
    } catch (Exception e) {
      // Ignore exceptions
    }
  }
}
