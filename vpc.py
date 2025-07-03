import boto3
from time import sleep
class VPC:
  """## create a vpc for your EKS cluster. """
  def __init__(self, profile, region, name):
    self.profile = profile
    self.region = region
    self.name = name
    session = boto3.session.Session(profile_name=self.profile)
    self.client = session.client('ec2',region_name=self.region)
  
  def create_vpc_only(self, CidrBlock, InstanceTenancy='default'):
    response = self.client.create_vpc(
    CidrBlock=CidrBlock,
    InstanceTenancy=InstanceTenancy,
    TagSpecifications=[
        {
            'ResourceType': 'vpc',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': self.name
                },
            ]
        },
    ]
    )
    self.vpc_id = response['Vpc']['VpcId']
    print("VPC created successfully")
    print(f'Name: {self.name}\nvpc_id: {self.vpc_id}')
  
  def set_vpcID(self,vpc_id):
    self.vpc_id = vpc_id

  def create_igw_only(self, name):
    response = self.client.create_internet_gateway(
    TagSpecifications=[
        {
            'ResourceType': 'internet-gateway',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': name
                },
            ]
        },
      ]
    )
    self.igw_id = response['InternetGateway']['InternetGatewayId']
    sleep(10)
    print(f'Internet gateway created successfully.\nName: {name}\nigw_id: {self.igw_id}')

  def attach_igw_to_vpc(self,igw_id,vpc_id):
    response = self.client.attach_internet_gateway(
        InternetGatewayId=igw_id,
        VpcId=vpc_id
    )
    print("VPC attached to igw.")

  def create_subnet_only(self,vpc_id,subnet_list):
    """subnet_list format: \n
    [
      {
        'Name': 'Subnet name', 'AvailabilityZone': 'AvailabilityZone --> us-east-1a,1b like that', 'CidrBlock': 'cidr block for partion'
      }
    ]"""
    output_list = []
    for i in subnet_list:
      response_subnet = self.client.create_subnet(
          TagSpecifications=[
              {
                  'ResourceType': 'subnet',
                  'Tags': [
                      {
                          'Key': 'Name',
                          'Value': i['Name']
                      },
                  ]
              },
          ],
          AvailabilityZone=i['AvailabilityZone'],
          CidrBlock=i['CidrBlock'],
          VpcId= vpc_id,
      )
      output_list.append(response_subnet)
    self.subnet_private = [output_list[i]['Subnet']['SubnetId'] for i in range(2)]
    self.subnet_public = [output_list[i]['Subnet']['SubnetId'] for i in range(2,4)]
    print("Subnets created successfully")
    print(f'Private subnets: {self.subnet_private}\nPublic subnets: {self.subnet_public}')
    
  def allocate_elastic_ip_only(self,name='nat'):
    # allocate elastic ip
    response_EIP = self.client.allocate_address(
      Domain='vpc',
      TagSpecifications=[
          {
              'ResourceType': 'elastic-ip',
              'Tags': [
                  {
                      'Key': 'Name',
                      'Value': name
                  },
              ]
          },
      ]
    )
    self.elasticIP = response_EIP['AllocationId']
    print(f'Elastic Ip created with the given subnet.\nElastic IP id: {self.elasticIP}')

  def create_nat_gateway_only(self,subnet_id,elasticIP,name='nat'):
    # create a nat gateway
    response_natGW = self.client.create_nat_gateway(
        AllocationId=elasticIP,
        SubnetId=subnet_id,
        TagSpecifications=[
            {
                'ResourceType': 'natgateway',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': name
                    },
                ]
            },
        ],
        ConnectivityType='public'
    )
    self.nat_gw_id = response_natGW['NatGateway']['NatGatewayId']
    sleep(20)
    print(f'Nat Gateway created.\n Nat GW id: {self.nat_gw_id}')
    
  def create_route_table_set_only(self,vpc_id):
    # create route table

    response_RT_PRT = self.client.create_route_table(
        VpcId=vpc_id,
        TagSpecifications=[
            {
                'ResourceType': 'route-table',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': 'private'
                    },
                ]
            },
        ]
    )
    response_RT_PUB = self.client.create_route_table(
        VpcId=vpc_id,
        TagSpecifications=[
            {
                'ResourceType': 'route-table',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': 'public'
                    },
                ]
            },
        ]
    )
    self.RT_PRT = response_RT_PRT['RouteTable']['RouteTableId']
    self.RT_PUB = response_RT_PUB['RouteTable']['RouteTableId']
    print("Route tables created successfully.")
  
  def create_routes(self,RT_PRT,RT_PUB,nat_gw_id,igw_id):
    """#### Always comes in pair private and public route"""
    # private route
    self.client.create_route(
        DestinationCidrBlock='0.0.0.0/0',
        NatGatewayId=nat_gw_id,
        RouteTableId=RT_PRT
    )
    # public route
    self.client.create_route(
        DestinationCidrBlock='0.0.0.0/0',
        GatewayId=igw_id,
        RouteTableId=RT_PUB
    )
  def associate_route_table(self):
    """#### associate route table to subnets\n
    Only subnets created by this class is allowed to be associated here for other subnets please associate from `AWS console`"""
    for i in self.subnet_public:
        self.client.associate_route_table(
            RouteTableId=self.RT_PUB,
            SubnetId=i
        )
    for i in self.subnet_private:
        self.client.associate_route_table(
            RouteTableId=self.RT_PRT,
            SubnetId=i
        )
    print("All rotes associated with the subnets.")

  def create_all_resourse(self,CidrBlock='10.0.0.0/16',skipVPCcreation=False,vpc_id=None):
    if not skipVPCcreation:
      self.create_vpc_only(CidrBlock)
    else:
      self.set_vpcID(vpc_id)
    self.create_igw_only('igw')
    self.attach_igw_to_vpc(self.igw_id, self.vpc_id)
    self.create_subnet_only(self.vpc_id,
                            [{'Name': f'EKS-private-{self.region}a', 'AvailabilityZone': f'{self.region}a', 'CidrBlock': '10.0.0.0/18'},
                             {'Name': f'EKS-private-{self.region}b', 'AvailabilityZone': f'{self.region}b', 'CidrBlock': '10.0.64.0/18'},
                             {'Name': f'EKS-public-{self.region}a', 'AvailabilityZone': f'{self.region}a', 'CidrBlock': '10.0.128.0/18'},
                             {'Name': f'EKS-public-{self.region}b', 'AvailabilityZone': f'{self.region}b', 'CidrBlock': '10.0.193.0/18'}])
    self.allocate_elastic_ip_only()
    self.create_nat_gateway_only(self.subnet_public[0],self.elasticIP)
    self.create_route_table_set_only(self.vpc_id)
    self.create_routes(self.RT_PRT,self.RT_PUB,self.nat_gw_id,self.igw_id)
    self.associate_route_table()
    print("VPC is all set for your EKS cluster.")
