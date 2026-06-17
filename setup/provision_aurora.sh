#!/usr/bin/env bash
# Provision an AWS Aurora PostgreSQL Serverless v2 cluster for Perseus Dashboard.
# 
# Prerequisites:
#   1. AWS CLI installed and configured (`aws configure`)
#   2. AWS promotional credits applied
#   3. Default VPC exists in the target region
#
# Usage: bash setup/provision_aurora.sh
# 
# This script:
#   1. Creates a DB subnet group (or uses default VPC subnets)
#   2. Creates an Aurora PostgreSQL Serverless v2 cluster
#   3. Creates a writer instance
#   4. Outputs the DATABASE_URL connection string

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration — edit these if needed
# ---------------------------------------------------------------------------
CLUSTER_ID="${CLUSTER_ID:-perseus-dashboard-h0}"
DB_NAME="${DB_NAME:-perseus_dashboard}"
DB_USERNAME="${DB_USERNAME:-perseus_admin}"
DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -base64 24)}"
REGION="${AWS_REGION:-us-east-1}"
INSTANCE_CLASS="${INSTANCE_CLASS:-db.serverless}"  # Aurora Serverless v2

echo "═══════════════════════════════════════════════"
echo " Provisioning AWS Aurora PostgreSQL (Serverless v2)"
echo " Cluster: $CLUSTER_ID"
echo " DB:      $DB_NAME"
echo " Region:  $REGION"
echo "═══════════════════════════════════════════════"

# 1. Find default VPC and its subnets
echo ""
echo "[1/5] Finding default VPC..."

VPC_ID=$(aws ec2 describe-vpcs \
    --region "$REGION" \
    --filters "Name=isDefault,Values=true" \
    --query "Vpcs[0].VpcId" \
    --output text 2>/dev/null)

if [ "$VPC_ID" = "None" ] || [ -z "$VPC_ID" ]; then
    echo "ERROR: No default VPC found in $REGION. Create one or set AWS_REGION to a region with a default VPC."
    exit 1
fi

echo "   VPC: $VPC_ID"

# Get subnet IDs
SUBNET_IDS=$(aws ec2 describe-subnets \
    --region "$REGION" \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query "Subnets[*].SubnetId" \
    --output text)

SUBNET_COUNT=$(echo "$SUBNET_IDS" | wc -w)
echo "   Subnets: $SUBNET_COUNT found"

if [ "$SUBNET_COUNT" -lt 1 ]; then
    echo "ERROR: No subnets in default VPC."
    exit 1
fi

# 2. Create DB subnet group
echo ""
echo "[2/5] Creating DB subnet group..."
SG_NAME="${CLUSTER_ID}-subnet-group"

# Delete if exists (idempotent re-run)
aws rds delete-db-subnet-group \
    --db-subnet-group-name "$SG_NAME" \
    --region "$REGION" 2>/dev/null || true

aws rds create-db-subnet-group \
    --db-subnet-group-name "$SG_NAME" \
    --db-subnet-group-description "Subnet group for Perseus Dashboard H0" \
    --subnet-ids $SUBNET_IDS \
    --region "$REGION" > /dev/null

echo "   Created: $SG_NAME"

# 3. Create security group for Aurora
echo ""
echo "[3/5] Creating security group..."
SG_ID=$(aws ec2 create-security-group \
    --group-name "${CLUSTER_ID}-sg" \
    --description "Aurora PostgreSQL access for Perseus Dashboard" \
    --vpc-id "$VPC_ID" \
    --region "$REGION" \
    --query "GroupId" \
    --output text 2>/dev/null || \
    aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=${CLUSTER_ID}-sg" \
        --region "$REGION" \
        --query "SecurityGroups[0].GroupId" \
        --output text)

# Allow PostgreSQL from anywhere (for hackathon demo — restrict in production!)
aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 5432 \
    --cidr 0.0.0.0/0 \
    --region "$REGION" 2>/dev/null || true

echo "   Security Group: $SG_ID"

# 4. Create Aurora PostgreSQL Serverless v2 cluster
echo ""
echo "[4/5] Creating Aurora cluster (takes ~5-10 minutes)..."

aws rds create-db-cluster \
    --db-cluster-identifier "$CLUSTER_ID" \
    --engine aurora-postgresql \
    --engine-version 16.4 \
    --engine-mode provisioned \
    --serverless-v2-scaling-configuration "MinCapacity=0.5,MaxCapacity=2.0" \
    --master-username "$DB_USERNAME" \
    --master-user-password "$DB_PASSWORD" \
    --db-subnet-group-name "$SG_NAME" \
    --vpc-security-group-ids "$SG_ID" \
    --database-name "$DB_NAME" \
    --region "$REGION" \
    --enable-http-endpoint \
    --storage-encrypted \
    --deletion-protection false \
    --backup-retention-period 1 \
    2>&1 | head -5

echo "   Cluster creation initiated: $CLUSTER_ID"

# 5. Create DB instance (Serverless v2 writer)
echo ""
echo "[5/5] Creating DB instance..."

aws rds create-db-instance \
    --db-instance-identifier "${CLUSTER_ID}-writer" \
    --db-cluster-identifier "$CLUSTER_ID" \
    --db-instance-class "$INSTANCE_CLASS" \
    --engine aurora-postgresql \
    --region "$REGION" \
    2>&1 | head -5

echo "   Instance creation initiated: ${CLUSTER_ID}-writer"

# 6. Wait for cluster to become available
echo ""
echo "Waiting for cluster to become available..."
aws rds wait db-cluster-available \
    --db-cluster-identifier "$CLUSTER_ID" \
    --region "$REGION"

# Get the writer endpoint
ENDPOINT=$(aws rds describe-db-clusters \
    --db-cluster-identifier "$CLUSTER_ID" \
    --region "$REGION" \
    --query "DBClusters[0].Endpoint" \
    --output text)

echo ""
echo "═══════════════════════════════════════════════"
echo " AURORA POSTGRESQL PROVISIONED"
echo "═══════════════════════════════════════════════"
echo ""
echo "  Endpoint:  $ENDPOINT"
echo "  Port:      5432"
echo "  Database:  $DB_NAME"
echo "  Username:  $DB_USERNAME"
echo "  Password:  $DB_PASSWORD"
echo ""
echo "  Connection string:"
echo "  postgresql://${DB_USERNAME}:${DB_PASSWORD}@${ENDPOINT}:5432/${DB_NAME}"
echo ""
echo "Add this to backend/.env:"
echo "  DATABASE_URL=postgresql://${DB_USERNAME}:${DB_PASSWORD}@${ENDPOINT}:5432/${DB_NAME}"
echo ""
echo "═══════════════════════════════════════════════"
echo ""
echo "Verification:"
echo "  PGPASSWORD='$DB_PASSWORD' psql -h $ENDPOINT -U $DB_USERNAME -d $DB_NAME -c 'SELECT 1;'"
echo ""
echo "⚠️  Save the password! It won't be shown again."
