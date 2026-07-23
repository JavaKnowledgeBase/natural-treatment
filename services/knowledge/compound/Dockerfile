FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /build

COPY services/knowledge/compound/pom.xml .
RUN mvn -q -B dependency:go-offline

COPY services/knowledge/compound/src ./src
RUN mvn -q -B -DskipTests package

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /build/target/app.jar app.jar

EXPOSE 8000
ENTRYPOINT ["java", "-Xmx160m", "-XX:MaxMetaspaceSize=96m", "-XX:+UseSerialGC", "-jar", "app.jar"]
