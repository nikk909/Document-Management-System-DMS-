-- 创建数据库脚本
-- 用于初始化文档元数据管理数据库

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS `20251213_document_metadata` 
    DEFAULT CHARACTER SET utf8mb4 
    DEFAULT COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE `20251213_document_metadata`;

-- 注意：表结构由 SQLAlchemy 自动创建
-- 此脚本仅用于创建数据库

