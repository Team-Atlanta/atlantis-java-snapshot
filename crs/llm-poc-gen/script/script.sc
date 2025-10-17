import io.shiftleft.codepropertygraph.generated.nodes.Call
import io.shiftleft.semanticcpg.dotgenerator.CfgGenerator
import io.shiftleft.semanticcpg.dotgenerator.DotSerializer.{Edge, Graph}
import io.joern.dataflowengineoss.semanticsloader.{FullNameSemanticsParser, Semantics, FlowSemantic}
import io.joern.dataflowengineoss.DefaultSemantics
import java.nio.file.{Files, Paths, StandardOpenOption}
import java.nio.charset.StandardCharsets
import org.json4s._
import org.json4s.native.JsonMethods._
import org.json4s.native.Serialization
import org.json4s.native.Serialization.writePretty
import org.json4s.JsonDSL._
import scala.io.Source
import scala.util.{Try, Success, Failure}
import scala.collection.mutable
import scala.util.control.Breaks._

object UserSemantic {
  def get_semantic_dir(): String = {
    Option(System.getenv("SEMANTIC_DIR")).getOrElse("")
  }

  def loadFlowSemantics(semanticPath: String): List[FlowSemantic] = {
    try {
      if (semanticPath.endsWith(".sem")) new FullNameSemanticsParser().parseFile(semanticPath) else List()
    } catch {
      case _ => List()
    }
  }

  def loadFlowSemanticsFromDir(semanticDir: String): List[FlowSemantic] = {
    try {
      val dirPath = Paths.get(semanticDir)
      val semPaths = Files.list(dirPath).iterator().asScala.toList
          .filterNot(path => Files.isDirectory(path))
          .filter(path => path.toString.endsWith(".sem"))
      semPaths.map(
        semanticPath => UserSemantic.loadFlowSemantics(semanticPath.toString)
      ).flatten
    } catch {
      case _ => List()
    }
  }

  def updateSemanticsFromDir(semanticDir: String): Unit = {
    DefaultSemantics.userSemantics ++= UserSemantic.loadFlowSemanticsFromDir(semanticDir)
  }
}

def clojure_lang_hooks(implicit cpg: Cpg) = {
  cpg.call
    .where(_.callee.fullName("clojure.lang.IFn.invoke:.*"))
    .argument
    .argumentIndex(1, 2)
}

def command_injection(implicit cpg: Cpg) = {
  cpg.call
    .where(_.callee.fullName("^java.lang.Process(Builder|Impl).start:.*"))
    .argument
    .argumentIndex(0) ++
    cpg.call
      .where(_.callee.fullName("^hudson.Launcher\\$ProcStarter.start:.*"))
      .argument
      .argumentIndex(0) ++
    cpg.call
      .where(_.callee.fullName("^org.apache.commons.exec.DefaultExecutor.execute:.*"))
      .argument
      .argumentIndex(1) ++
    cpg.call
      .where(_.callee.fullName("^java.lang.Runtime.exec:.*"))
      .argument
      .argumentIndex(1, 2) ++
    cpg.call
      .where(_.callee.fullName("^javax.xml.transform.Transformer.transform:void\\(javax.xml.transform.Source.*"))
      .argument
      .argumentIndex(1) ++
    cpg.call
      .where(_.callee.fullNameExact("java.lang.reflect.Constructor.newInstance:java.lang.Object(java.lang.Object[])"))
      .argument
      .argumentIndex(1)
}

def deserialization(implicit cpg: Cpg) = {
  def readSink = cpg.call
    .where(_.callee.fullName(
      "java.io.ObjectInputStream.read(Object|ObjectOverride|Unshared):.*"
    ))
    .whereNot(_.file.method.nameExact("fuzzerTestOneInput"))
    .argument
    .argumentIndex(0)
  def initSink = cpg.call
    .where(_.callee.fullName("java.io.ObjectInputStream.<init>:.*"))
    .whereNot(_.file.method.nameExact("fuzzerTestOneInput"))
    .argument
    .argumentIndex(1)

  def forName = cpg.argument
    .where(_.inCall.methodFullName("java.lang.Class.forName:java.lang.Class\\(java.lang.String.*"))
    .where(_.argumentIndex(1))
    .whereNot(_.isLiteral)
  def newInstance = cpg.argument
    .where(_.inCall.methodFullNameExact("java.lang.reflect.Constructor.newInstance:java.lang.Object(java.lang.Object[])"))
    .where(_.argumentIndex(1))

  (readSink.reachableByFlows(initSink) ++ newInstance.reachableByFlows(forName))
    .map(_.elements.lastOption)
    .collect{case Some(a) => a}
    .collect{case a: Expression => a}
    ++ cpg.call
      .where(_.callee.fullName(
        List(
          "java.beans.XMLDecoder.readObject:.*",
          "java.io.ObjectInputStream.readObject:.*",
          "java.rmi.MarshalledObject.get:.*",
          "javax.management.remote.rmi.RMIConnectorServer.start:.*",
          "com.caucho.hessian.io.HessianInput.readObject:.*",
          "flex.messaging.io.amf.Amf3Input.readObject:.*",
        ) *
      ))
      .argument
      .argumentIndex(0) ++
    cpg.call
      .where(_.callee.fullName(
        List(
          "org.apache.commons.lang3.SerializationUtils.deserialize:.*",
          "org.springframework.core.serializer.DefaultDeserializer.deserialize:.*",
          "org.springframework.web.util.WebUtils.deserializeFromByteArray:.*",
          "com.thoughtworks.xstream.XStream.fromXML:.*",
          "com.fasterxml.jackson.databind.ObjectMapper.readValue:.*",
          "com.esotericsoftware.kryo.Kryo.readClassAndObject:.*",
          "org.yaml.snakeyaml.Yaml.load:.*",
          "com.owlike.genson.Genson.deserialize:.*",
        ) *
      ))
      .argument
      .argumentIndex(1)
}

def el_injection(implicit cpg: Cpg) = {
  cpg.call
    .where(_.callee.fullName(
      "(javax|jakarta).el.ExpressionFactory.create(Method|Value)Expression:.*"
    ))
    .argument.argumentIndex(2) ++
    cpg.call
      .where(_.callee.fullName(
        "javax.validation.ConstraintValidatorContext.buildConstraintViolationWithTemplate:.*"
      ))
      .argument
      .argumentIndex(1)
}

def ldap_injection(implicit cpg: Cpg) = {
  cpg.call
    .where(_.callee.fullName("^javax.naming.directory.(Initial)?DirContext.search:.*"))
    .argument
    .argumentIndex(1, 2)
}

def naming_context_look_up(implicit cpg: Cpg) = {
  cpg.call
    .where(_.callee.fullName("^org.apache.logging.log4j.Logger.(error|fatal|warn|info|debug|trace):.*"))
    .argument
    .argumentIndex(1) ++
    cpg.call
      .where(_.callee.fullName("javax.naming..*Context.lookup(Link)?:.*"))
      .argument
      .argumentIndex(1)
}

def reflective_call(implicit cpg: Cpg) = {
  val sinkArgs = Iterator(
    (
      Set(
        "^java.lang.Class.forName:.*",
        "^java.lang.ClassLoader.loadClass:.*"
      ),
      1
    ),
    (
      Set(
        "^java.lang.Class.forName:.*",
        "^java.lang.ClassLoader.loadClass:.*"
      ),
      2
    ),
    (
      Set(
        "^java.lang.(Runtime|System).load(Library)?:.*",
        "^java.lang.System.mapLibraryName:.*",
        "^java.lang.ClassLoader.findLibrary:.*",
        "^java.lang.Runtime.load:.*",
        "^java.nio.file.Files.(copy|move):.*"
      ),
      1
    )
  )
  sinkArgs.flatMap(e => {
    val methods = e._1
    val argNo = e._2
    cpg.call
      .where(_.callee.fullName(methods.toSeq *))
      .argument
      .argumentIndex(argNo)
      .where(_.typ.fullName("java.lang.String"))
  })
}

def regex_injection(implicit cpg: Cpg) = {
  cpg.call
    .where(_.callee.fullName(
      List(
        "^java.util.regex.Pattern.(compile|matches):.*",
        "^java.lang.String.(matches|replaceAll|replaceFirst|split):.*"
      ) *
    ))
    .argument
    .argumentIndex(1)
}

def script_injection(implicit cpg: Cpg) = {
  cpg.call
    .where(_.callee.fullName(
      List(
        "^javax.script.ScriptEngine.eval:.*",
        "^groovy.lang.GroovyShell.evaluate:.*",
        "^org.apache.commons.jexl3.JexlExpression.evaluate:.*",
        "^org.apache.commons.jexl3.JxltEngine.Expression.evaluate:.*",
        "^ognl.Ognl.getValue:.*",
        "^org.apache.commons.ognl.Ognl.getValue:.*",
        "^bsh.Interpreter.(eval|get):.*",
        "^org.springframework.expression.(Spel)?ExpressionParser.parseExpression:.*",
      ) *
    ))
    .argument
    .argumentIndex(1) ++
    cpg.call
      .where(_.callee.fullName(
        List(
          "^java.lang.reflect.Method.invoke:.*",
          "^java.lang.ClassLoader.defineClass.define:.*",
          "^javax.tools.JavaCompiler.run:.*",
          "^org.mvel2.MVEL.executeExpression:.*",
          "^org.mozilla.javascript.Context.evaluate(String|Reader):.*",
        ) *
      ))
      .argument
}

def sql_injection(implicit cpg: Cpg) = {
  cpg.call
    .where(_.callee.fullName(
      "^java.sql.Statement.(execute(Batch|LargeBatch|LargeUpdate|Query|Update)?|createNativeQuery):.*"
    ))
    .argument
    .argumentIndex(1)
}

def ssrf(implicit cpg: Cpg) = {
  cpg.call
    .where(_.callee.fullName(
      List(
        "java.net.SocketImpl.connect:.*",
        "java.net.Socket.connect:.*",
        "java.net.SocksSocketImpl:.*",
        "java.nio.channels.SocketChannel.connect:.*",
        "sun.nio.ch.SocketAdaptor.connect:.*",
        "jdk.internal.net.http.PlainHttpConnection.connect:.*"
      ) *
    ))
    .argument
    .argumentIndex(1, 2) ++
    cpg.call
      .where(_.callee.fullName("^java.net.http.HttpClient.send:.*"))
      .argument
      .argumentIndex(1) ++
    cpg.call
      .where(_.callee.fullName("^java.net.Socket.<init>:.*"))
      .argument
      .argumentIndex(1) ++
    cpg.argument
      .where(_.inCall.methodFullNameExact("java.net.URLConnection.getInputStream:java.io.InputStream()"))
      .where(_.argumentIndex(0)) ++
    cpg.call.methodFullName("^java.net.URL.open(Connection|Stream):.*")
      .whereNot(_.file.method.nameExact("fuzzerTestOneInput"))
      .argument
      .argumentIndex(0)
      .reachableBy(
        cpg.call
          .where(_.callee.fullName("^java.net.URL.<init>:.*"))
          .whereNot(_.file.method.nameExact("fuzzerTestOneInput"))
          .argument
          .argumentIndex(1)
      ) ++
    cpg.call
      .where(_.callee.fullName(
        List(
          "^org.apache.http.impl.client.CloseableHttpClient.execute:.*",
          "^org.apache.http.impl.nio.client.CloseableHttpAsyncClient.execute:.*",
          "^org.apache.http.client.HttpClient.execute:.*",
          "^org.apache.http.client.fluent.Request.(Get|Patch|Post|Put|Delete).execute:.*",
          "^okhttp3.OkHttpClient.newCall:.*",
          "^org.springframework.web.client.RestTemplate.getForObject:.*",
        ) *
      ))
      .whereNot(_.file.method.nameExact("fuzzerTestOneInput"))
      .argument
      .argumentIndex(1) ++
    cpg.call
      .where(_.callee.fullName("javax.xml.transform.Transformer.transform:void\\(javax.xml.transform.Source.*"))
      .argument
      .argumentIndex(1) ++
    cpg.call
      .where(_.callee.fullName("^org.xml.sax.XMLReader.parse:void\\(org.xml.sax.InputSource.*"))
      .argument
      .argumentIndex(1) ++
    cpg.call
      .where(_.callee.fullName("javax.xml.parsers.SAXParser.parse:void\\(java.io.InputStream.*"))
      .argument
      .argumentIndex(1) ++
    cpg.call
      .where(_.callee.fullNameExact("java.net.URLConnection.getContentType:java.lang.String()"))
      .argument
      .argumentIndex(0)
}

def xpath_injection(implicit cpg: Cpg) = {
  cpg.call
    .where(_.callee.fullName(
      "^(jenkins.util.xml.XMLUtils.parse|javax.xml.xpath.XPath.(compile|evaluate|evaluateExpression)):.*"
    ))
    .argument
    .argumentIndexGt(0)
}

def arbitrary_file_read_write(implicit cpg: Cpg) = {
  val sinkArgs = Iterator(
    (
      Set(
        "^java.nio.file.Files.newByteChannel:.*",
        "^java.nio.file.Files.newBufferedReader:.*",
        "^java.nio.file.Files.newBufferedWriter:.*",
        "^java.nio.file.Files.readString:.*",
        "^java.nio.file.Files.readAllBytes:.*",
        "^java.nio.file.Files.readAllLines:.*",
        "^java.nio.file.Files.readSymbolicLink:.*",
        "^java.nio.file.Files.write:.*",
        "^java.nio.file.Files.writeString:.*",
        "^java.nio.file.Files.newInputStream:.*",
        "^java.nio.file.Files.newOutputStream:.*",
        "^java.nio.channels.FileChannel.open:.*"
      ),
      1,
      Set("java.nio.file.Path")
    ),
    (
      Set(
        "^java.nio.file.Files.copy:.*",
        "^java.nio.file.Files.move:.*"
      ),
      2,
      Set("java.nio.file.Path")
    ),
    (
      Set(
        "^java.io.FileReader.<init>:.*",
        "^java.io.FileWriter.<init>:.*",
        "^java.io.FileInputStream.<init>:.*",
        "^java.io.FileOutputStream.<init>:.*",
        "^java.io.FileOutputStream.<init>:.*"
      ),
      1,
      Set("java.lang.String", "java.io.File")
    ),
    (
      Set("^java.util.Scanner.<init>:.*"),
      1,
      Set("java.lang.String", "java.nio.file.Path", "java.io.File")
    ),
    (Set("^org.apache.commons.fileupload.FileItem.write:.*"), 1, Set(".*"))
  )
  sinkArgs.flatMap(e => {
    val methods = e._1
    val argNo = e._2
    val types = e._3
    cpg.call
      .where(_.callee.fullName(methods.toSeq *))
      .argument
      .argumentIndex(argNo)
      .where(_.typ.fullName(types.toSeq *))
  }) ++
    cpg.call
      .where(_.callee.fullName(
        List(
          "javax.servlet.http.Part.write:.*",
          "org.apache.commons.fileupload.FileItem.write:.*",
          "org.springframework.web.multipart.MultipartFile.transferTo:.*",
        ) *
      ))
      .argument
      .argumentIndex(0, 1) ++
    cpg.call
      .where(_.callee.fullName(
        List(
          "org.apache.commons.io.FileUtils.copyInputStreamToFile:.*",
          "java.nio.file.Files.copy:.*"
        ) *
      ))
      .argument
      .argumentIndex(1, 2) ++
    cpg.call
      .where(_.callee.fullName(
        List(
          "org.apache.commons.io.FileUtils.readFileToString:.*",
          "org.springframework.core.io.ResourceLoader.getResource:.*",
          "javax.servlet.ServletContext.getResource:.*",
          "javax.servlet.ServletContext.getResourceAsStream:.*",
        ) *
      ))
      .argument
      .argumentIndex(1)
}

def update_semantics = {
  UserSemantic.updateSemanticsFromDir(UserSemantic.get_semantic_dir())
  semantics = DefaultSemantics()
}
