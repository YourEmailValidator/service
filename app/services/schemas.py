from pydantic import BaseModel


class EmailResponse(BaseModel):
    email: str
    is_valid: bool
    message: str = None


class EmailRequest(BaseModel):
    email: str


class DonaturEmailRequest(BaseModel):
    email: list[str]
    allow_smtputf8: bool = False
    allow_empty_local: bool = False
    allow_quoted_local: bool = False
    allow_domain_literal: bool = False
    allow_display_name: bool = False
    check_deliverability: bool = True
    test_environment: bool = False
    globally_deliverable: bool = True
    timeout: int = 10
