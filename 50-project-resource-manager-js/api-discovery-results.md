# API Discovery Results

## S/4HANA Cloud APIs — Project & Resource Management

| API Name | ORD ID | Type | Files Available |
|---|---|---|---|
| Project Demand | `sap.s4:apiResource:API_PROJECTDEMAND_0001:v1` | OData | EDMX, OpenAPI JSON |
| Resource Assignment Source for Project Demands | `sap.s4:apiResource:CE_PROJDEMANDSOURCEOFSUPPLY_0001:v1` | OData | EDMX, OpenAPI JSON |
| Workforce Daily Availability | `sap.s4:apiResource:API_MANAGE_WF_AVAILABILITY:v1` | OData | EDMX, OpenAPI JSON |
| Assignment Status for Project Demands - Read | `sap.s4:apiResource:CE_PROJDEMANDASSIGNMENTSTATUS_0001:v1` | OData | EDMX, OpenAPI JSON |
| Project Demand Status - Read | `sap.s4:apiResource:CE_PROJECTDEMANDSTATUS_0001:v1` | OData | EDMX, OpenAPI JSON |

## SAP SuccessFactors APIs — Employee Central

| API Name | ORD ID | Type | Files Available |
|---|---|---|---|
| Skills Management | `sap.sf:apiResource:ECSkillsManagement:v1` | OData | EDMX, OpenAPI JSON |
| Employee Profile | `sap.sf:apiResource:ECEmployeeProfile:v1` | OData | EDMX, OpenAPI JSON |
| Employment Information | `sap.sf:apiResource:ECEmploymentInformation:v1` | OData | EDMX, OpenAPI JSON |
| Personal Information | `sap.sf:apiResource:ECPersonalInformation:v1` | OData | EDMX, OpenAPI JSON |
| Employee Global Information | `sap.sf:apiResource:EmployeeCentralEC:v1` | OData | EDMX, OpenAPI JSON |

## Selected APIs (in scope for this agent)

The following 6 APIs are used by the agent — EDMX specs saved in `specification/project-resource-management-agent/api-specs/`:

1. `specification/project-resource-management-agent/api-specs/project-demand.edmx` → `sap.s4:apiResource:API_PROJECTDEMAND_0001:v1`
2. `specification/project-resource-management-agent/api-specs/resource-assignment-source.edmx` → `sap.s4:apiResource:CE_PROJDEMANDSOURCEOFSUPPLY_0001:v1`
3. `specification/project-resource-management-agent/api-specs/workforce-daily-availability.edmx` → `sap.s4:apiResource:API_MANAGE_WF_AVAILABILITY:v1`
4. `specification/project-resource-management-agent/api-specs/sf-skills-management.edmx` → `sap.sf:apiResource:ECSkillsManagement:v1`
5. `specification/project-resource-management-agent/api-specs/sf-employee-profile.edmx` → `sap.sf:apiResource:ECEmployeeProfile:v1`
6. `specification/project-resource-management-agent/api-specs/sf-employment-information.edmx` → `sap.sf:apiResource:ECEmploymentInformation:v1`
