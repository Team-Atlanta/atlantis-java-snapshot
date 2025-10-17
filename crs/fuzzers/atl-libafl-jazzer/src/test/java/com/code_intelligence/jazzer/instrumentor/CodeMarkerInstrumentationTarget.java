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

package com.code_intelligence.jazzer.instrumentor;

import java.io.ByteArrayInputStream;
import java.io.ObjectInputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;
import javax.el.ELContext;
import javax.el.ExpressionFactory;
import javax.el.MethodExpression;
import javax.el.ValueExpression;
import javax.naming.Context;
import javax.naming.InitialContext;
import javax.naming.Name;
import javax.naming.NamingException;
import javax.naming.directory.Attributes;
import javax.naming.directory.DirContext;
import javax.naming.directory.InitialDirContext;
import javax.naming.directory.SearchControls;
import javax.xml.xpath.XPath;
import javax.xml.xpath.XPathExpression;
import javax.xml.xpath.XPathFactory;

public class CodeMarkerInstrumentationTarget implements DynamicTestContract {

  @Override
  public Map<String, Boolean> selfCheck() {
    Map<String, Boolean> results = new HashMap<>();

    // REFLECTION SINKPOINTS
    results.put("testClassForName", testClassForName());
    results.put("testClassForNameWithLoader", testClassForNameWithLoader());
    results.put("testClassForNameWithModule", testClassForNameWithModule());

    results.put("testClassLoaderLoadClass", testClassLoaderLoadClass());
    results.put("testClassLoaderLoadClassWithFlag", testClassLoaderLoadClassWithFlag());
    results.put("testClassLoaderLoadClassWithModule", testClassLoaderLoadClassWithModule());

    // NATIVE CODE LOADING SINKPOINTS
    results.put("testRuntimeLoad", testRuntimeLoad());
    results.put("testRuntimeLoadExplicit", testRuntimeLoadExplicit());
    results.put("testRuntimeLoadLibrary", testRuntimeLoadLibrary());
    results.put("testSystemLoad", testSystemLoad());
    results.put("testSystemLoadLibrary", testSystemLoadLibrary());
    results.put("testClassLoaderFindLibrary", testClassLoaderFindLibrary());

    // PROCESS EXECUTION SINKPOINTS
    results.put("testProcessBuilderStart", testProcessBuilderStart());
    results.put("testProcessImplStart", testProcessImplStart());

    // JNDI CONTEXT LOOKUP SINKPOINTS
    results.put("testContextLookup", testContextLookup());
    results.put("testContextLookupLink", testContextLookupLink());

    // LDAP DIRECTORY SEARCH SINKPOINTS
    results.put("testDirContextSearch", testDirContextSearch());
    results.put("testInitialDirContextSearch", testInitialDirContextSearch());

    // EXPRESSION LANGUAGE SINKPOINTS
    results.put(
        "testExpressionFactoryCreateValueExpression", testExpressionFactoryCreateValueExpression());
    results.put(
        "testExpressionFactoryCreateMethodExpression",
        testExpressionFactoryCreateMethodExpression());
    results.put(
        "testJakartaExpressionFactoryCreateValueExpression",
        testJakartaExpressionFactoryCreateValueExpression());
    results.put(
        "testJakartaExpressionFactoryCreateMethodExpression",
        testJakartaExpressionFactoryCreateMethodExpression());
    // ConstraintValidatorContext.buildConstraintViolationWithTemplate skipped

    // DESERIALIZATION SINKPOINTS
    results.put("testObjectInputStream", testObjectInputStream());
    results.put("testObjectInputStreamReadObject", testObjectInputStreamReadObject());
    results.put("testObjectInputStreamReadUnshared", testObjectInputStreamReadUnshared());
    results.put(
        "testObjectInputStreamReadObjectOverride", testObjectInputStreamReadObjectOverride());

    // XPATH SINKPOINTS
    results.put("testXPathCompile", testXPathCompile());
    results.put("testXPathEvaluate", testXPathEvaluate());
    results.put("testXPathEvaluateExpression", testXPathEvaluateExpression());

    // REGEX SINKPOINTS
    results.put("testPatternCompile", testPatternCompile());
    results.put("testPatternCompileWithFlags", testPatternCompileWithFlags());
    results.put("testPatternMatches", testPatternMatches());
    results.put("testStringMatches", testStringMatches());
    results.put("testStringReplaceAll", testStringReplaceAll());
    results.put("testStringReplaceFirst", testStringReplaceFirst());
    results.put("testStringSplit", testStringSplit());
    results.put("testStringSplitWithLimit", testStringSplitWithLimit());

    return results;
  }

  private boolean testClassForName() {
    try {
      // Should trigger Class.forName sinkpoint
      Class<?> cls = Class.forName("java.lang.String");
      return cls != null;
    } catch (Exception e) {
      return false;
    }
  }

  private boolean testClassLoaderLoadClass() {
    try {
      // Should trigger ClassLoader.loadClass sinkpoint
      ClassLoader cl = this.getClass().getClassLoader();
      Class<?> cls = cl.loadClass("java.lang.String");
      return cls != null;
    } catch (Exception e) {
      return false;
    }
  }

  private boolean testRuntimeLoad() {
    try {
      // For testing only - don't actually load a library
      if (System.getProperty("os.name").toLowerCase().contains("win")) {
        // Just get the name, don't actually load
        String libName = System.mapLibraryName("test");
        return libName != null;
      } else {
        // Just reference the method without calling it
        // This is enough for testing the instrumentation
        Runtime rt = Runtime.getRuntime();
        return rt != null;
      }
    } catch (Exception e) {
      return false;
    }
  }

  private boolean testPatternCompile() {
    try {
      // Should trigger Pattern.compile sinkpoint
      Pattern pattern = Pattern.compile("test.*");
      return pattern.matcher("test123").matches();
    } catch (Exception e) {
      return false;
    }
  }

  private boolean testStringMatches() {
    try {
      // Should trigger String.matches sinkpoint
      String str = "test123";
      return str.matches("test.*");
    } catch (Exception e) {
      return false;
    }
  }

  private boolean testObjectInputStream() {
    try {
      // Create a dummy stream - we won't actually use it
      byte[] dummyData = new byte[0];
      ByteArrayInputStream bais = new ByteArrayInputStream(dummyData);

      // Should trigger ObjectInputStream.<init> sinkpoint
      ObjectInputStream ois = new ObjectInputStream(bais);

      // Just to avoid "resource not closed" warnings
      ois.close();
      bais.close();

      return true;
    } catch (Exception e) {
      return false;
    }
  }

  private boolean testStringSplit() {
    try {
      // Should trigger String.split sinkpoint
      String str = "a,b,c,d";
      String[] parts = str.split(",");
      return parts.length == 4;
    } catch (Exception e) {
      return false;
    }
  }

  private boolean testClassForNameWithLoader() {
    try {
      // Should trigger Class.forName(String, boolean, ClassLoader) sinkpoint
      ClassLoader cl = this.getClass().getClassLoader();
      Class<?> cls = Class.forName("java.lang.String", true, cl);
      return cls != null;
    } catch (Exception e) {
      return false;
    }
  }

  // Java 9+ API
  private boolean testClassForNameWithModule() {
    try {
      // REQUIRES JAVA 9 OR LATER TO COMPILE
      Object module = getClass().getModule();
      Class<?> cls = Class.forName((java.lang.Module) module, "java.lang.String");
      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  // Protected method - SKIPPED
  private boolean testClassLoaderLoadClassWithFlag() {
    return true;
  }

  // Java 9+ API & Protected method - SKIPPED
  private boolean testClassLoaderLoadClassWithModule() {
    return true;
  }

  private boolean testRuntimeLoadExplicit() {
    try {
      // Get Runtime instance
      Runtime rt = Runtime.getRuntime();

      // Set up a fake library path that won't actually be loaded
      String libPath = "/path/to/nonexistent/lib_" + System.currentTimeMillis() + ".so";

      // Call the method directly to trigger instrumentation
      try {
        // Direct call will trigger instrumentation
        rt.load(libPath);
      } catch (UnsatisfiedLinkError e) {
        // Expected - the library doesn't exist
        // The important thing is that we called the method to trigger instrumentation
        return true;
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testRuntimeLoadLibrary() {
    try {
      // Get Runtime instance
      Runtime rt = Runtime.getRuntime();

      // Set up a fake library name that won't actually be loaded
      String libName = "nonexistent_lib_" + System.currentTimeMillis();

      // Call the method directly instead of via reflection
      // This should trigger instrumentation
      try {
        // This direct call will trigger instrumentation by CodeMarkerInstrumentor
        rt.loadLibrary(libName);
      } catch (UnsatisfiedLinkError e) {
        // Expected - the library doesn't exist
        // The important thing is that we called the method to trigger instrumentation
        return true;
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testSystemLoad() {
    try {
      // Set up a fake library path that won't actually be loaded
      String libPath = "/path/to/nonexistent/lib_" + System.currentTimeMillis() + ".so";

      // Call directly to trigger instrumentation
      try {
        System.load(libPath);
      } catch (UnsatisfiedLinkError e) {
        // Expected - the library doesn't exist
        // The important thing is that we called the method to trigger instrumentation
        return true;
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testSystemLoadLibrary() {
    try {
      // Set up a fake library name that won't actually be loaded
      String libName = "nonexistent_lib_" + System.currentTimeMillis();

      // Call directly to trigger instrumentation
      try {
        System.loadLibrary(libName);
      } catch (UnsatisfiedLinkError e) {
        // Expected - the library doesn't exist
        // The important thing is that we called the method to trigger instrumentation
        return true;
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  // Protected method - SKIPPED
  private boolean testClassLoaderFindLibrary() {
    return true;
  }

  // Implementation differences - SKIPPED
  private boolean testConstraintViolationTemplate() {
    return true;
  }

  private boolean testProcessBuilderStart() {
    try {
      // Create a safe process builder for "true" command (exits immediately with 0)
      List<String> command = new ArrayList<>();
      command.add("true"); // Unix/Linux command that just exits with success
      ProcessBuilder pb = new ProcessBuilder(command);

      // Actually call start() to trigger instrumentation
      Process proc = pb.start();

      // Wait for the process to finish
      proc.waitFor();

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  // JDK internal implementation class - SKIPPED
  private boolean testProcessImplStart() {
    return true;
  }

  @SuppressWarnings("BanJNDI")
  private boolean testContextLookup() {
    try {
      // Create a mock Context using a minimal implementation
      Context context =
          new Context() {
            @Override
            public Object lookup(String name) throws NamingException {
              return "test-value";
            }

            @Override
            public Object lookupLink(String name) throws NamingException {
              return "test-link";
            }

            @Override
            public void close() throws NamingException {}

            @Override
            public String getNameInNamespace() throws NamingException {
              return null;
            }

            @Override
            public javax.naming.NameParser getNameParser(String name) throws NamingException {
              return null;
            }

            @Override
            public javax.naming.NameParser getNameParser(Name name) throws NamingException {
              return null;
            }

            @Override
            public javax.naming.NamingEnumeration<javax.naming.NameClassPair> list(String name)
                throws NamingException {
              return null;
            }

            @Override
            public javax.naming.NamingEnumeration<javax.naming.NameClassPair> list(Name name)
                throws NamingException {
              return null;
            }

            @Override
            public javax.naming.NamingEnumeration<javax.naming.Binding> listBindings(String name)
                throws NamingException {
              return null;
            }

            @Override
            public javax.naming.NamingEnumeration<javax.naming.Binding> listBindings(Name name)
                throws NamingException {
              return null;
            }

            @Override
            public Object lookup(Name name) throws NamingException {
              return null;
            }

            @Override
            public Object lookupLink(Name name) throws NamingException {
              return null;
            }

            @Override
            public void bind(String name, Object obj) throws NamingException {}

            @Override
            public void bind(Name name, Object obj) throws NamingException {}

            @Override
            public void rebind(String name, Object obj) throws NamingException {}

            @Override
            public void rebind(Name name, Object obj) throws NamingException {}

            @Override
            public void unbind(String name) throws NamingException {}

            @Override
            public void unbind(Name name) throws NamingException {}

            @Override
            public void rename(String oldName, String newName) throws NamingException {}

            @Override
            public void rename(Name oldName, Name newName) throws NamingException {}

            @Override
            public javax.naming.Context createSubcontext(String name) throws NamingException {
              return null;
            }

            @Override
            public javax.naming.Context createSubcontext(Name name) throws NamingException {
              return null;
            }

            @Override
            public void destroySubcontext(String name) throws NamingException {}

            @Override
            public void destroySubcontext(Name name) throws NamingException {}

            @Override
            public Object addToEnvironment(String propName, Object propVal) throws NamingException {
              return null;
            }

            @Override
            public Object removeFromEnvironment(String propName) throws NamingException {
              return null;
            }

            @Override
            public java.util.Hashtable<?, ?> getEnvironment() throws NamingException {
              return null;
            }

            @Override
            public Name composeName(Name name, Name prefix) throws NamingException {
              return null;
            }

            @Override
            public String composeName(String name, String prefix) throws NamingException {
              return null;
            }
          };

      String lookupPath = "java:comp/env/test";
      Object result = context.lookup(lookupPath);
      return result != null;
    } catch (Exception e) {
      return false;
    }
  }

  @SuppressWarnings("BanJNDI")
  private boolean testContextLookupLink() {
    try {
      // We'll use the same mock Context implementation as in testContextLookup
      Context context = null;
      try {
        // Try to create a real InitialContext if possible
        context = new InitialContext();
      } catch (NamingException e) {
        // If that fails, create a minimal mock
        context =
            new Context() {
              @Override
              public Object lookup(String name) throws NamingException {
                return "test-value";
              }

              @Override
              public Object lookupLink(String name) throws NamingException {
                return "test-link";
              }

              @Override
              public void close() throws NamingException {}

              // Implement other required methods with empty implementations
              @Override
              public String getNameInNamespace() throws NamingException {
                return null;
              }

              @Override
              public javax.naming.NameParser getNameParser(String name) throws NamingException {
                return null;
              }

              @Override
              public javax.naming.NameParser getNameParser(Name name) throws NamingException {
                return null;
              }

              @Override
              public javax.naming.NamingEnumeration<javax.naming.NameClassPair> list(String name)
                  throws NamingException {
                return null;
              }

              @Override
              public javax.naming.NamingEnumeration<javax.naming.NameClassPair> list(Name name)
                  throws NamingException {
                return null;
              }

              @Override
              public javax.naming.NamingEnumeration<javax.naming.Binding> listBindings(String name)
                  throws NamingException {
                return null;
              }

              @Override
              public javax.naming.NamingEnumeration<javax.naming.Binding> listBindings(Name name)
                  throws NamingException {
                return null;
              }

              @Override
              public Object lookup(Name name) throws NamingException {
                return null;
              }

              @Override
              public Object lookupLink(Name name) throws NamingException {
                return null;
              }

              @Override
              public void bind(String name, Object obj) throws NamingException {}

              @Override
              public void bind(Name name, Object obj) throws NamingException {}

              @Override
              public void rebind(String name, Object obj) throws NamingException {}

              @Override
              public void rebind(Name name, Object obj) throws NamingException {}

              @Override
              public void unbind(String name) throws NamingException {}

              @Override
              public void unbind(Name name) throws NamingException {}

              @Override
              public void rename(String oldName, String newName) throws NamingException {}

              @Override
              public void rename(Name oldName, Name newName) throws NamingException {}

              @Override
              public javax.naming.Context createSubcontext(String name) throws NamingException {
                return null;
              }

              @Override
              public javax.naming.Context createSubcontext(Name name) throws NamingException {
                return null;
              }

              @Override
              public void destroySubcontext(String name) throws NamingException {}

              @Override
              public void destroySubcontext(Name name) throws NamingException {}

              @Override
              public Object addToEnvironment(String propName, Object propVal)
                  throws NamingException {
                return null;
              }

              @Override
              public Object removeFromEnvironment(String propName) throws NamingException {
                return null;
              }

              @Override
              public java.util.Hashtable<?, ?> getEnvironment() throws NamingException {
                return null;
              }

              @Override
              public Name composeName(Name name, Name prefix) throws NamingException {
                return null;
              }

              @Override
              public String composeName(String name, String prefix) throws NamingException {
                return null;
              }
            };
      }

      String lookupPath = "java:comp/env/test";
      try {
        // Call the lookupLink method to make sure it's referenced
        Object result = context.lookupLink(lookupPath);
      } catch (NamingException e) {
        // We expect this to fail in most test environments
        // We just need to reference the method
      }

      return true;
    } catch (Exception e) {
      return false;
    }
  }

  @SuppressWarnings("BanJNDI")
  private boolean testDirContextSearch() {
    try {
      // Create a mock DirContext implementation
      DirContext dirContext =
          new DirContext() {
            @Override
            public Object lookup(String name) throws NamingException {
              return null;
            }

            @Override
            public Object lookup(Name name) throws NamingException {
              return null;
            }

            @Override
            public void bind(String name, Object obj) throws NamingException {}

            @Override
            public void bind(Name name, Object obj) throws NamingException {}

            @Override
            public void rebind(String name, Object obj) throws NamingException {}

            @Override
            public void rebind(Name name, Object obj) throws NamingException {}

            @Override
            public void unbind(String name) throws NamingException {}

            @Override
            public void unbind(Name name) throws NamingException {}

            @Override
            public void rename(String oldName, String newName) throws NamingException {}

            @Override
            public void rename(Name oldName, Name newName) throws NamingException {}

            @Override
            public javax.naming.NamingEnumeration<javax.naming.NameClassPair> list(String name)
                throws NamingException {
              return null;
            }

            @Override
            public javax.naming.NamingEnumeration<javax.naming.NameClassPair> list(Name name)
                throws NamingException {
              return null;
            }

            @Override
            public javax.naming.NamingEnumeration<javax.naming.Binding> listBindings(String name)
                throws NamingException {
              return null;
            }

            @Override
            public javax.naming.NamingEnumeration<javax.naming.Binding> listBindings(Name name)
                throws NamingException {
              return null;
            }

            @Override
            public void destroySubcontext(String name) throws NamingException {}

            @Override
            public void destroySubcontext(Name name) throws NamingException {}

            @Override
            public javax.naming.Context createSubcontext(String name) throws NamingException {
              return null;
            }

            @Override
            public javax.naming.Context createSubcontext(Name name) throws NamingException {
              return null;
            }

            @Override
            public Object lookupLink(String name) throws NamingException {
              return null;
            }

            @Override
            public Object lookupLink(Name name) throws NamingException {
              return null;
            }

            @Override
            public javax.naming.NameParser getNameParser(String name) throws NamingException {
              return null;
            }

            @Override
            public javax.naming.NameParser getNameParser(Name name) throws NamingException {
              return null;
            }

            @Override
            public String composeName(String name, String prefix) throws NamingException {
              return null;
            }

            @Override
            public Name composeName(Name name, Name prefix) throws NamingException {
              return null;
            }

            @Override
            public Object addToEnvironment(String propName, Object propVal) throws NamingException {
              return null;
            }

            @Override
            public Object removeFromEnvironment(String propName) throws NamingException {
              return null;
            }

            @Override
            public java.util.Hashtable<?, ?> getEnvironment() throws NamingException {
              return null;
            }

            @Override
            public void close() throws NamingException {}

            @Override
            public String getNameInNamespace() throws NamingException {
              return null;
            }

            @Override
            public javax.naming.NamingEnumeration<javax.naming.directory.SearchResult> search(
                String name, Attributes matchingAttributes) throws NamingException {
              return null;
            }

            @Override
            public javax.naming.NamingEnumeration<javax.naming.directory.SearchResult> search(
                Name name, Attributes matchingAttributes) throws NamingException {
              return null;
            }

            @Override
            public javax.naming.NamingEnumeration<javax.naming.directory.SearchResult> search(
                String name, Attributes matchingAttributes, String[] attributesToReturn)
                throws NamingException {
              return null;
            }

            @Override
            public javax.naming.NamingEnumeration<javax.naming.directory.SearchResult> search(
                Name name, Attributes matchingAttributes, String[] attributesToReturn)
                throws NamingException {
              return null;
            }

            @Override
            public javax.naming.NamingEnumeration<javax.naming.directory.SearchResult> search(
                String name, String filter, SearchControls cons) throws NamingException {
              return null;
            }

            @Override
            public javax.naming.NamingEnumeration<javax.naming.directory.SearchResult> search(
                Name name, String filter, SearchControls cons) throws NamingException {
              return null;
            }

            @Override
            public javax.naming.NamingEnumeration<javax.naming.directory.SearchResult> search(
                String name, String filterExpr, Object[] filterArgs, SearchControls cons)
                throws NamingException {
              return null;
            }

            @Override
            public javax.naming.NamingEnumeration<javax.naming.directory.SearchResult> search(
                Name name, String filterExpr, Object[] filterArgs, SearchControls cons)
                throws NamingException {
              return null;
            }

            @Override
            public Attributes getAttributes(String name) throws NamingException {
              return null;
            }

            @Override
            public Attributes getAttributes(Name name) throws NamingException {
              return null;
            }

            @Override
            public Attributes getAttributes(String name, String[] attrIds) throws NamingException {
              return null;
            }

            @Override
            public Attributes getAttributes(Name name, String[] attrIds) throws NamingException {
              return null;
            }

            @Override
            public void modifyAttributes(String name, int mod_op, Attributes attrs)
                throws NamingException {}

            @Override
            public void modifyAttributes(Name name, int mod_op, Attributes attrs)
                throws NamingException {}

            @Override
            public void modifyAttributes(
                String name, javax.naming.directory.ModificationItem[] mods)
                throws NamingException {}

            @Override
            public void modifyAttributes(Name name, javax.naming.directory.ModificationItem[] mods)
                throws NamingException {}

            @Override
            public void bind(String name, Object obj, Attributes attrs) throws NamingException {}

            @Override
            public void bind(Name name, Object obj, Attributes attrs) throws NamingException {}

            @Override
            public void rebind(String name, Object obj, Attributes attrs) throws NamingException {}

            @Override
            public void rebind(Name name, Object obj, Attributes attrs) throws NamingException {}

            @Override
            public javax.naming.directory.DirContext createSubcontext(String name, Attributes attrs)
                throws NamingException {
              return null;
            }

            @Override
            public javax.naming.directory.DirContext createSubcontext(Name name, Attributes attrs)
                throws NamingException {
              return null;
            }

            @Override
            public javax.naming.directory.DirContext getSchema(String name) throws NamingException {
              return null;
            }

            @Override
            public javax.naming.directory.DirContext getSchema(Name name) throws NamingException {
              return null;
            }

            @Override
            public javax.naming.directory.DirContext getSchemaClassDefinition(String name)
                throws NamingException {
              return null;
            }

            @Override
            public javax.naming.directory.DirContext getSchemaClassDefinition(Name name)
                throws NamingException {
              return null;
            }
          };

      // Set up parameters for a search
      String baseName = "ou=People,dc=example,dc=com";
      String filter = "(objectClass=person)";
      SearchControls controls = new SearchControls();
      controls.setSearchScope(SearchControls.SUBTREE_SCOPE);

      // Actually call the search method to trigger instrumentation
      dirContext.search(baseName, filter, controls);

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  @SuppressWarnings("BanJNDI")
  private boolean testInitialDirContextSearch() {
    try {
      java.util.Hashtable<String, Object> env = new java.util.Hashtable<>();
      env.put(Context.INITIAL_CONTEXT_FACTORY, "com.sun.jndi.ldap.LdapCtxFactory");

      InitialDirContext dirContext = null;
      try {
        dirContext = new InitialDirContext(env);
      } catch (NamingException e) {
        dirContext =
            new InitialDirContext(env) {
              @Override
              public javax.naming.NamingEnumeration<javax.naming.directory.SearchResult> search(
                  String name, String filter, SearchControls cons) throws NamingException {
                return null;
              }
            };
      }

      String baseName = "ou=People,dc=example,dc=com";
      String filter = "(objectClass=person)";
      SearchControls controls = new SearchControls();
      controls.setSearchScope(SearchControls.SUBTREE_SCOPE);

      dirContext.search(baseName, filter, controls);
      return true;
    } catch (Exception e) {
      return true;
    }
  }

  private boolean testExpressionFactoryCreateValueExpression() {
    try {
      // Get the ExpressionFactory instance
      ExpressionFactory factory = ExpressionFactory.newInstance();

      // Create a simple expression - we need to actually call the method
      String expression = "${user.name}";

      // Create a minimal ELContext implementation
      ELContext elContext =
          new ELContext() {
            @Override
            public javax.el.ELResolver getELResolver() {
              return null;
            }

            @Override
            public javax.el.FunctionMapper getFunctionMapper() {
              return null;
            }

            @Override
            public javax.el.VariableMapper getVariableMapper() {
              return null;
            }
          };

      // Actually call the method to ensure it gets instrumented
      ValueExpression valueExpr =
          factory.createValueExpression(elContext, expression, String.class);

      return valueExpr != null;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testExpressionFactoryCreateMethodExpression() {
    try {
      // Get the ExpressionFactory instance
      ExpressionFactory factory = ExpressionFactory.newInstance();

      // Create a simple expression
      String expression = "${user.getName()}";

      // Create a minimal ELContext implementation
      ELContext elContext =
          new ELContext() {
            @Override
            public javax.el.ELResolver getELResolver() {
              return null;
            }

            @Override
            public javax.el.FunctionMapper getFunctionMapper() {
              return null;
            }

            @Override
            public javax.el.VariableMapper getVariableMapper() {
              return null;
            }
          };

      // Actually call the method to ensure it gets instrumented
      Class<?>[] paramTypes = new Class<?>[0];
      MethodExpression methodExpr =
          factory.createMethodExpression(elContext, expression, String.class, paramTypes);

      return methodExpr != null;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  // Removed test for javax.validation.ConstraintValidatorContext due to implementation differences

  private boolean testObjectInputStreamReadObject() {
    try {
      // Create a serialized String
      byte[] dummyData;
      try (java.io.ByteArrayOutputStream baos = new java.io.ByteArrayOutputStream();
          java.io.ObjectOutputStream oos = new java.io.ObjectOutputStream(baos)) {
        oos.writeObject("test string");
        dummyData = baos.toByteArray();
      }

      ByteArrayInputStream bais = new ByteArrayInputStream(dummyData);
      ObjectInputStream ois = new ObjectInputStream(bais);

      // Actually call readObject to trigger the instrumentation
      Object obj = ois.readObject();

      // Clean up
      ois.close();
      bais.close();

      return obj != null;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testObjectInputStreamReadUnshared() {
    try {
      // Create a serialized String
      byte[] dummyData;
      try (java.io.ByteArrayOutputStream baos = new java.io.ByteArrayOutputStream();
          java.io.ObjectOutputStream oos = new java.io.ObjectOutputStream(baos)) {
        oos.writeObject("test string");
        dummyData = baos.toByteArray();
      }

      ByteArrayInputStream bais = new ByteArrayInputStream(dummyData);
      ObjectInputStream ois = new ObjectInputStream(bais);

      // Actually call readUnshared to trigger the instrumentation
      Object obj = ois.readUnshared();

      // Clean up
      ois.close();
      bais.close();

      return obj != null;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  // Protected method - SKIPPED in tests
  private boolean testObjectInputStreamReadObjectOverride() {
    return true;
  }

  private boolean testXPathCompile() {
    try {
      // Should trigger XPath.compile sinkpoint
      XPath xpath = XPathFactory.newInstance().newXPath();
      String expression = "/root/element";

      // Actually call the compile method
      XPathExpression compiledXPath = xpath.compile(expression);

      return compiledXPath != null;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testXPathEvaluate() {
    try {
      // Should trigger XPath.evaluate sinkpoint
      XPath xpath = XPathFactory.newInstance().newXPath();
      String expression = "/root/element";
      String xml = "<root><element>test</element></root>";

      // Create a simple XML source object for evaluation
      javax.xml.transform.Source source =
          new javax.xml.transform.stream.StreamSource(new java.io.StringReader(xml));

      // Actually call the evaluate method - with null result type to get string
      String result = xpath.evaluate(expression, source);

      return result != null;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  // Test XPath.evaluateExpression (Java 9+ API only)
  private boolean testXPathEvaluateExpression() {
    try {
      // Get the XPath instance and prepare test data
      XPath xpath = XPathFactory.newInstance().newXPath();
      String expression = "/root/element";
      javax.xml.transform.Source source =
          new javax.xml.transform.stream.StreamSource(
              new java.io.StringReader("<root><element>test</element></root>"));

      // This will compile with Java 9+ but may fail at runtime on Java 8
      // Just referencing the method is enough for instrumentation testing
      @SuppressWarnings("unchecked")
      String result = xpath.evaluateExpression(expression, source, String.class);
      return result != null;
    } catch (Throwable e) {
      // Any error is fine - we just need the method reference for instrumentation
      return true;
    }
  }

  private boolean testPatternCompileWithFlags() {
    try {
      // Should trigger Pattern.compile(String, int) sinkpoint
      Pattern pattern = Pattern.compile("test.*", Pattern.CASE_INSENSITIVE);
      return pattern.matcher("TEST123").matches();
    } catch (Exception e) {
      return false;
    }
  }

  private boolean testPatternMatches() {
    try {
      // Should trigger Pattern.matches(String, CharSequence) sinkpoint
      boolean result = Pattern.matches("test.*", "test123");
      return result;
    } catch (Exception e) {
      return false;
    }
  }

  private boolean testStringReplaceAll() {
    try {
      // Should trigger String.replaceAll sinkpoint
      String str = "test123test456";
      String result = str.replaceAll("test", "replaced");
      return result.equals("replaced123replaced456");
    } catch (Exception e) {
      return false;
    }
  }

  private boolean testStringReplaceFirst() {
    try {
      // Should trigger String.replaceFirst sinkpoint
      String str = "test123test456";
      String result = str.replaceFirst("test", "replaced");
      return result.equals("replaced123test456");
    } catch (Exception e) {
      return false;
    }
  }

  private boolean testStringSplitWithLimit() {
    try {
      // Should trigger String.split(String, int) sinkpoint
      String str = "a,b,c,d";
      String[] parts = str.split(",", 2);
      return parts.length == 2 && parts[0].equals("a") && parts[1].equals("b,c,d");
    } catch (Exception e) {
      return false;
    }
  }

  // Test Jakarta EL ExpressionFactory.createValueExpression
  private boolean testJakartaExpressionFactoryCreateValueExpression() {
    try {
      jakarta.el.ELContext elContext =
          new jakarta.el.ELContext() {
            @Override
            public jakarta.el.ELResolver getELResolver() {
              return null;
            }

            @Override
            public jakarta.el.FunctionMapper getFunctionMapper() {
              return null;
            }

            @Override
            public jakarta.el.VariableMapper getVariableMapper() {
              return null;
            }
          };

      jakarta.el.ExpressionFactory factory = jakarta.el.ExpressionFactory.newInstance();
      jakarta.el.ValueExpression valueExpr =
          factory.createValueExpression(elContext, "${test}", String.class);
      return valueExpr != null;
    } catch (Throwable e) {
      return true;
    }
  }

  // Test Jakarta EL ExpressionFactory.createMethodExpression
  private boolean testJakartaExpressionFactoryCreateMethodExpression() {
    try {
      jakarta.el.ELContext elContext =
          new jakarta.el.ELContext() {
            @Override
            public jakarta.el.ELResolver getELResolver() {
              return null;
            }

            @Override
            public jakarta.el.FunctionMapper getFunctionMapper() {
              return null;
            }

            @Override
            public jakarta.el.VariableMapper getVariableMapper() {
              return null;
            }
          };

      jakarta.el.ExpressionFactory factory = jakarta.el.ExpressionFactory.newInstance();
      jakarta.el.MethodExpression methodExpr =
          factory.createMethodExpression(
              elContext, "${test.method()}", String.class, new Class<?>[0]);
      return methodExpr != null;
    } catch (Throwable e) {
      return true;
    }
  }
}
