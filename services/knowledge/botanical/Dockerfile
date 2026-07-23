FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /build

COPY services/knowledge/botanical/pom.xml .
RUN mvn -q -B dependency:go-offline

COPY services/knowledge/botanical/src ./src
RUN mvn -q -B -DskipTests package

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /build/target/app.jar app.jar

EXPOSE 8000
ENTRYPOINT ["java", "-jar", "app.jar"]
