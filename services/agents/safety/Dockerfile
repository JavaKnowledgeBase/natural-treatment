FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /build

COPY services/agents/safety/pom.xml .
RUN mvn -q -B dependency:go-offline

COPY services/agents/safety/src ./src
RUN mvn -q -B -DskipTests package

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /build/target/app.jar app.jar

EXPOSE 8000
ENTRYPOINT ["java", "-Xmx192m", "-XX:MaxMetaspaceSize=96m", "-XX:+UseSerialGC", "-jar", "app.jar"]
