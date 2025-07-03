# eks

# Create VPC with subnets and everything.

## Usage:

```bash
git clone git@github.com:intellizone/eks.git
cd VPC_creation
```
### Example
```python
from VPC import VPC
vpc=VPC(profile='default', region='us-east-1', name='EKS-VPC')
vpc.create_all_resourse(CidrBlock='10.0.0.0/16')
# to print subnets
print(vpc.subnet_public)
print(vpc.subnet_private)
```
