import { ForbiddenException, NotFoundException, ServiceUnavailableException } from '@nestjs/common';

export class RippleBrainOrgNotFoundException extends NotFoundException {
  constructor(organizationId: string) {
    // A valid id from another tenant reads as "not found" rather than
    // confirming that the organization exists.
    super(`Organization not found: ${organizationId}`);
  }
}

export class RippleBrainAccessDeniedException extends ForbiddenException {
  constructor(action: string) {
    super(`You do not have permission to ${action} RippleBrain analyses`);
  }
}

export class RippleBrainEngineException extends ServiceUnavailableException {
  constructor() {
    super('Analysis engine is unavailable');
  }
}
