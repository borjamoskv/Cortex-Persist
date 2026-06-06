# ComplianceReport

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Status** | **string** |  | 
**LedgerValid** | **bool** |  | 
**TotalTrustScore** | **float32** |  | 
**AuditCoverage** | **float32** |  | 
**ComplianceLevel** | **string** |  | 
**Article12Status** | **string** |  | 

## Methods

### NewComplianceReport

`func NewComplianceReport(status string, ledgerValid bool, totalTrustScore float32, auditCoverage float32, complianceLevel string, article12Status string, ) *ComplianceReport`

NewComplianceReport instantiates a new ComplianceReport object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewComplianceReportWithDefaults

`func NewComplianceReportWithDefaults() *ComplianceReport`

NewComplianceReportWithDefaults instantiates a new ComplianceReport object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetStatus

`func (o *ComplianceReport) GetStatus() string`

GetStatus returns the Status field if non-nil, zero value otherwise.

### GetStatusOk

`func (o *ComplianceReport) GetStatusOk() (*string, bool)`

GetStatusOk returns a tuple with the Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStatus

`func (o *ComplianceReport) SetStatus(v string)`

SetStatus sets Status field to given value.


### GetLedgerValid

`func (o *ComplianceReport) GetLedgerValid() bool`

GetLedgerValid returns the LedgerValid field if non-nil, zero value otherwise.

### GetLedgerValidOk

`func (o *ComplianceReport) GetLedgerValidOk() (*bool, bool)`

GetLedgerValidOk returns a tuple with the LedgerValid field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLedgerValid

`func (o *ComplianceReport) SetLedgerValid(v bool)`

SetLedgerValid sets LedgerValid field to given value.


### GetTotalTrustScore

`func (o *ComplianceReport) GetTotalTrustScore() float32`

GetTotalTrustScore returns the TotalTrustScore field if non-nil, zero value otherwise.

### GetTotalTrustScoreOk

`func (o *ComplianceReport) GetTotalTrustScoreOk() (*float32, bool)`

GetTotalTrustScoreOk returns a tuple with the TotalTrustScore field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTotalTrustScore

`func (o *ComplianceReport) SetTotalTrustScore(v float32)`

SetTotalTrustScore sets TotalTrustScore field to given value.


### GetAuditCoverage

`func (o *ComplianceReport) GetAuditCoverage() float32`

GetAuditCoverage returns the AuditCoverage field if non-nil, zero value otherwise.

### GetAuditCoverageOk

`func (o *ComplianceReport) GetAuditCoverageOk() (*float32, bool)`

GetAuditCoverageOk returns a tuple with the AuditCoverage field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAuditCoverage

`func (o *ComplianceReport) SetAuditCoverage(v float32)`

SetAuditCoverage sets AuditCoverage field to given value.


### GetComplianceLevel

`func (o *ComplianceReport) GetComplianceLevel() string`

GetComplianceLevel returns the ComplianceLevel field if non-nil, zero value otherwise.

### GetComplianceLevelOk

`func (o *ComplianceReport) GetComplianceLevelOk() (*string, bool)`

GetComplianceLevelOk returns a tuple with the ComplianceLevel field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetComplianceLevel

`func (o *ComplianceReport) SetComplianceLevel(v string)`

SetComplianceLevel sets ComplianceLevel field to given value.


### GetArticle12Status

`func (o *ComplianceReport) GetArticle12Status() string`

GetArticle12Status returns the Article12Status field if non-nil, zero value otherwise.

### GetArticle12StatusOk

`func (o *ComplianceReport) GetArticle12StatusOk() (*string, bool)`

GetArticle12StatusOk returns a tuple with the Article12Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetArticle12Status

`func (o *ComplianceReport) SetArticle12Status(v string)`

SetArticle12Status sets Article12Status field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


