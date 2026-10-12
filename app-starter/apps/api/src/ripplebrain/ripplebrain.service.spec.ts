import { OrgRole } from '@prisma/client';
import { ConfigService } from '@nestjs/config';
import { PrismaService } from '../prisma/prisma.service';
import { OrganizationsService } from '../organizations/organizations.service';
import { RippleBrainService } from './ripplebrain.service';
import {
  RippleBrainAccessDeniedException,
  RippleBrainOrgNotFoundException,
} from './exceptions/ripplebrain.exceptions';

describe('RippleBrainService', () => {
  const userId = 'user-1';
  const organizationId = 'org-1';

  const mockPrisma = {
    rippleBrainRun: { create: jest.fn(), findMany: jest.fn() },
  };

  const mockOrganizationsService = {
    getUserRoleInOrganization: jest.fn(),
  };

  const mockConfigService = {
    get: jest.fn((key: string, fallback?: string) => {
      if (key === 'RIPPLEBRAIN_ENGINE_URL') return 'http://engine:8000';
      if (key === 'RIPPLEBRAIN_INTERNAL_TOKEN') return 'token';
      return fallback;
    }),
  };

  const buildService = () =>
    new RippleBrainService(
      mockPrisma as unknown as PrismaService,
      mockOrganizationsService as unknown as OrganizationsService,
      mockConfigService as unknown as ConfigService,
    );

  beforeEach(() => {
    jest.clearAllMocks();
    mockPrisma.rippleBrainRun.create.mockResolvedValue({});
    mockPrisma.rippleBrainRun.findMany.mockResolvedValue([]);
  });

  it('analyze throws NotFound when the caller has no role in the organization', async () => {
    // Arrange
    mockOrganizationsService.getUserRoleInOrganization.mockResolvedValue(null);
    const inputService = buildService();

    // Act
    const inputAction = inputService.analyze(userId, 'foreign-org', { changeRequest: '0123456789+' });

    // Assert
    await expect(inputAction).rejects.toBeInstanceOf(RippleBrainOrgNotFoundException);
  });

  it('approve throws Forbidden when the caller is only a MEMBER', async () => {
    // Arrange
    mockOrganizationsService.getUserRoleInOrganization.mockResolvedValue(OrgRole.MEMBER);
    const inputService = buildService();

    // Act
    const inputAction = inputService.approve(userId, organizationId, 'act_1', {});

    // Assert
    await expect(inputAction).rejects.toBeInstanceOf(RippleBrainAccessDeniedException);
  });

  it('analyze calls the engine with the internal token and audits the run', async () => {
    // Arrange
    mockOrganizationsService.getUserRoleInOrganization.mockResolvedValue(OrgRole.MEMBER);
    const fetchSpy = jest.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ analysis_id: 'an_1', summary: 'summary' }),
    } as Response);
    const inputService = buildService();

    // Act
    const actualResult = await inputService.analyze(userId, organizationId, {
      changeRequest: 'Our refund policy changes from 30 days to 14 days.',
    });

    // Assert
    expect(fetchSpy).toHaveBeenCalledWith(
      'http://engine:8000/api/changes/analyze',
      expect.objectContaining({
        headers: expect.objectContaining({ 'X-Internal-Token': 'token' }),
      }),
    );
    expect(mockPrisma.rippleBrainRun.create).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({ organizationId, actorId: userId, kind: 'ANALYZE' }),
      }),
    );
    expect((actualResult as { analysis_id: string }).analysis_id).toBe('an_1');
    fetchSpy.mockRestore();
  });

  it('listRuns returns only rows for the requested organization', async () => {
    // Arrange
    mockOrganizationsService.getUserRoleInOrganization.mockResolvedValue(OrgRole.ADMIN);
    mockPrisma.rippleBrainRun.findMany.mockResolvedValue([]);
    const inputService = buildService();

    // Act
    await inputService.listRuns(userId, organizationId);

    // Assert
    expect(mockPrisma.rippleBrainRun.findMany).toHaveBeenCalledWith(
      expect.objectContaining({ where: { organizationId } }),
    );
  });
});
