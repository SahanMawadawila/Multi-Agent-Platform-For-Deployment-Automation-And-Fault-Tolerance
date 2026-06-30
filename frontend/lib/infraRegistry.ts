export const infraRegistry: Record<string, any> = {
  "postgresql": {
    "display_name": "PostgreSQL",
    "category": "database",
    "default_image": "postgres:16-alpine",
    "supported_versions": ["17-alpine", "16-alpine", "15-alpine", "14-alpine"],
    "default_port": 5432,
    "default_credentials": {
      "db_user": { "env_key": "POSTGRES_USER", "default": "postgres" },
      "db_password": { "env_key": "POSTGRES_PASSWORD", "default": "auto_generate" },
      "db_name": { "env_key": "POSTGRES_DB", "default": "{project_id}_db" }
    },
    "connection_env_templates": {
      "jdbc": "jdbc:postgresql://{service_name}:{port}/{db_name}",
      "url": "postgresql://{db_user}:{db_password}@{service_name}:{port}/{db_name}",
      "spring_datasource_url": "jdbc:postgresql://{service_name}:{port}/{db_name}"
    },
    "client_version_map": {
      "spring-boot-2.x": "14-alpine",
      "spring-boot-3.x": "16-alpine",
      "prisma": "16-alpine",
      "sequelize": "16-alpine",
      "typeorm": "16-alpine",
      "django": "16-alpine",
      "sqlalchemy": "16-alpine"
    },
    "default_storage": { "size": "1Gi", "storage_class": "gp2" },
    "default_resources": {
      "cpu_request": "200m", "memory_request": "256Mi",
      "cpu_limit": "500m", "memory_limit": "512Mi"
    },
    "template_name": "postgresql"
  },

  "mongodb": {
    "display_name": "MongoDB",
    "category": "database",
    "default_image": "mongo:7.0",
    "supported_versions": ["7.0", "6.0", "5.0"],
    "default_port": 27017,
    "default_credentials": {
      "db_user": { "env_key": "MONGO_INITDB_ROOT_USERNAME", "default": "admin" },
      "db_password": { "env_key": "MONGO_INITDB_ROOT_PASSWORD", "default": "auto_generate" },
      "db_name": { "env_key": "MONGO_INITDB_DATABASE", "default": "{project_id}_db" }
    },
    "connection_env_templates": {
      "url": "mongodb://{db_user}:{db_password}@{service_name}:{port}/{db_name}?authSource=admin",
      "spring_data_mongodb_uri": "mongodb://{db_user}:{db_password}@{service_name}:{port}/{db_name}?authSource=admin"
    },
    "client_version_map": {
      "mongoose-6.x": "7.0",
      "mongoose-5.x": "5.0",
      "spring-data-mongodb": "7.0",
      "pymongo": "7.0"
    },
    "default_storage": { "size": "1Gi", "storage_class": "gp2" },
    "default_resources": {
      "cpu_request": "200m", "memory_request": "256Mi",
      "cpu_limit": "500m", "memory_limit": "512Mi"
    },
    "template_name": "mongodb"
  },

  "mysql": {
    "display_name": "MySQL",
    "category": "database",
    "default_image": "mysql:8.0",
    "supported_versions": ["8.4", "8.0", "5.7"],
    "default_port": 3306,
    "default_credentials": {
      "db_user": { "env_key": "MYSQL_USER", "default": "app_user" },
      "db_password": { "env_key": "MYSQL_PASSWORD", "default": "auto_generate" },
      "db_name": { "env_key": "MYSQL_DATABASE", "default": "{project_id}_db" },
      "root_password": { "env_key": "MYSQL_ROOT_PASSWORD", "default": "auto_generate" }
    },
    "connection_env_templates": {
      "jdbc": "jdbc:mysql://{service_name}:{port}/{db_name}",
      "url": "mysql://{db_user}:{db_password}@{service_name}:{port}/{db_name}",
      "spring_datasource_url": "jdbc:mysql://{service_name}:{port}/{db_name}"
    },
    "client_version_map": {
      "mysql2": "8.0",
      "spring-boot-3.x": "8.0",
      "spring-boot-2.x": "8.0",
      "django-mysql": "8.0",
      "sqlalchemy-mysql": "8.0"
    },
    "default_storage": { "size": "1Gi", "storage_class": "gp2" },
    "default_resources": {
      "cpu_request": "200m", "memory_request": "512Mi",
      "cpu_limit": "500m", "memory_limit": "1Gi"
    },
    "template_name": "mysql"
  },

  "redis": {
    "display_name": "Redis",
    "category": "cache",
    "default_image": "redis:7-alpine",
    "supported_versions": ["7-alpine", "6-alpine"],
    "default_port": 6379,
    "default_credentials": {},
    "connection_env_templates": {
      "url": "redis://{service_name}:{port}",
      "spring_redis_host": "{service_name}",
      "spring_redis_port": "{port}"
    },
    "client_version_map": {
      "ioredis": "7-alpine",
      "redis-py": "7-alpine",
      "spring-data-redis": "7-alpine",
      "jedis": "7-alpine"
    },
    "default_storage": null,
    "default_resources": {
      "cpu_request": "100m", "memory_request": "128Mi",
      "cpu_limit": "300m", "memory_limit": "256Mi"
    },
    "template_name": "redis"
  },

  "rabbitmq": {
    "display_name": "RabbitMQ",
    "category": "message_broker",
    "default_image": "rabbitmq:3.13-management-alpine",
    "supported_versions": ["3.13-management-alpine", "3.12-management-alpine"],
    "default_port": 5672,
    "management_port": 15672,
    "default_credentials": {
      "rabbitmq_user": { "env_key": "RABBITMQ_DEFAULT_USER", "default": "guest" },
      "rabbitmq_password": { "env_key": "RABBITMQ_DEFAULT_PASS", "default": "auto_generate" }
    },
    "connection_env_templates": {
      "url": "amqp://{rabbitmq_user}:{rabbitmq_password}@{service_name}:{port}",
      "spring_rabbitmq_host": "{service_name}",
      "spring_rabbitmq_port": "{port}",
      "spring_rabbitmq_username": "{rabbitmq_user}",
      "spring_rabbitmq_password": "{rabbitmq_password}"
    },
    "client_version_map": {
      "amqplib": "3.13-management-alpine",
      "spring-amqp": "3.13-management-alpine",
      "pika": "3.13-management-alpine"
    },
    "default_storage": { "size": "1Gi", "storage_class": "gp2" },
    "default_resources": {
      "cpu_request": "200m", "memory_request": "256Mi",
      "cpu_limit": "500m", "memory_limit": "512Mi"
    },
    "template_name": "rabbitmq"
  },

  "kafka": {
    "display_name": "Apache Kafka",
    "category": "message_broker",
    "default_image": "confluentinc/cp-kafka:7.6.0",
    "zookeeper_image": "confluentinc/cp-zookeeper:7.6.0",
    "supported_versions": ["7.6.0", "7.5.0", "7.4.0"],
    "default_port": 9092,
    "internal_port": 29092,
    "zookeeper_port": 2181,
    "default_credentials": {},
    "connection_env_templates": {
      "bootstrap_servers": "{service_name}:{internal_port}",
      "spring_kafka_bootstrap_servers": "{service_name}:{internal_port}"
    },
    "client_version_map": {
      "kafkajs": "7.6.0",
      "spring-kafka-3.x": "7.6.0",
      "spring-kafka-2.x": "7.4.0",
      "confluent-kafka-python": "7.6.0",
      "node-rdkafka": "7.6.0"
    },
    "default_storage": { "size": "1Gi", "storage_class": "gp2" },
    "default_resources": {
      "cpu_request": "500m", "memory_request": "1Gi",
      "cpu_limit": "1", "memory_limit": "2Gi"
    },
    "template_name": "kafka"
  }
};
