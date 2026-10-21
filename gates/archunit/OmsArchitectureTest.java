package com.brokerdealer.guardrails;

// Plumbline Guardrails — ArchUnit rules for the Broker-Dealer OMS.
// STATUS: written but NOT executed in the authoring environment (Maven Central was blocked).
// Run locally:  add com.tngtech.archunit:archunit-junit5 (test scope) to each service pom,
//               copy this class to services/<svc>/src/test/java/com/brokerdealer/guardrails/,
//               then `mvn -pl services/<svc> test -Dtest=OmsArchitectureTest`.
// Covers the type-aware rules Semgrep cannot express (CLAUDE.md §3, §4, §13c, §13g).

import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;
import jakarta.persistence.Entity;
import org.springframework.web.bind.annotation.RestController;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.*;
import static com.tngtech.archunit.library.Architectures.layeredArchitecture;
import static com.tngtech.archunit.library.GeneralCodingRules.*;

@AnalyzeClasses(packages = "com.brokerdealer", importOptions = ImportOption.DoNotIncludeTests.class)
class OmsArchitectureTest {

    // C5 / §4 — controller → service → repository, never skipping a layer
    @ArchTest
    static final ArchRule layers = layeredArchitecture().consideringOnlyDependenciesInLayers()
            .layer("Controller").definedBy("..controller..")
            .layer("Service").definedBy("..service..")
            .layer("Repository").definedBy("..repository..")
            .whereLayer("Controller").mayNotBeAccessedByAnyLayer()
            .whereLayer("Service").mayOnlyBeAccessedByLayers("Controller", "Service")
            .whereLayer("Repository").mayOnlyBeAccessedByLayers("Service");

    // C5 / §13g — services never expose JPA entities
    @ArchTest
    static final ArchRule servicesReturnDtos = methods()
            .that().areDeclaredInClassesThat().resideInAPackage("..service..")
            .and().arePublic()
            .should().notHaveRawReturnType(com.tngtech.archunit.base.DescribedPredicate.describe(
                    "a JPA @Entity", c -> c.isAnnotatedWith(Entity.class)))
            .because("CLAUDE.md §13g: NEVER expose JPA entities from service methods");

    // C5 / §3 — no cross-service package dependencies
    @ArchTest
    static final ArchRule noCrossServiceImports = slicesNoCycles();

    static ArchRule slicesNoCycles() {
        return com.tngtech.archunit.library.dependencies.SlicesRuleDefinition.slices()
                .matching("com.brokerdealer.(*)..").should().notDependOnEachOther()
                .because("CLAUDE.md §3: cross-service access via REST or Kafka only");
    }

    // C4 / §13e — no field injection
    @ArchTest
    static final ArchRule noFieldInjection = NO_CLASSES_SHOULD_USE_FIELD_INJECTION;

    // C5 / §10, §11 — no Reactor, no ApplicationEvent
    @ArchTest
    static final ArchRule noReactor = noClasses().should().dependOnClassesThat()
            .resideInAnyPackage("reactor..", "org.springframework.web.reactive..");

    @ArchTest
    static final ArchRule noApplicationEvents = noClasses().should().dependOnClassesThat()
            .areAssignableTo(org.springframework.context.ApplicationEvent.class);

    // C1 / §13a — no legacy date types (JwtService exempt: JJWT API takes java.util.Date)
    @ArchTest
    static final ArchRule noLegacyDates = noClasses().that().doNotHaveSimpleName("JwtService")
            .should().dependOnClassesThat().areAssignableTo(java.util.Date.class)
            .orShould().dependOnClassesThat().areAssignableTo(java.util.Calendar.class);

    // C2 / §13c — controllers live in .controller and carry the suffix
    @ArchTest
    static final ArchRule controllerPlacement = classes().that().areAnnotatedWith(RestController.class)
            .should().resideInAPackage("..controller..").andShould().haveSimpleNameEndingWith("Controller");

    // C9 / §13i — custom exceptions extend RuntimeException
    @ArchTest
    static final ArchRule exceptionsAreRuntime = classes().that().resideInAPackage("..exception..")
            .and().haveSimpleNameEndingWith("Exception")
            .should().beAssignableTo(RuntimeException.class);

    // C8 — no System.out / generic java.util.logging
    @ArchTest
    static final ArchRule noStdStreams = NO_CLASSES_SHOULD_ACCESS_STANDARD_STREAMS;
}
