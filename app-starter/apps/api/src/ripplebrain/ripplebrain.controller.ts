import { Body, Controller, Get, HttpCode, HttpStatus, Param, Post, Request, UseGuards } from '@nestjs/common';
import { ApiOperation, ApiResponse, ApiTags } from '@nestjs/swagger';
import { TokenPayload } from '@app-starter/shared';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { EmailVerifiedGuard } from '../auth/email-verified.guard';
import { RippleBrainService } from './ripplebrain.service';
import { AnalyzeRippleBrainDto } from './dto/analyze-ripplebrain.dto';
import { RippleBrainDecisionDto } from './dto/ripplebrain-decision.dto';

/**
 * Organization-scoped RippleBrain routes.
 *
 * The organization id sits in the path so tenant scoping is visible at the
 * route level. Membership and role checks happen in the service layer, where
 * the JWT subject is resolved against the route's organization id — a client
 * supplied organizationId alone never authenticates anyone.
 */
@ApiTags('ripplebrain')
@Controller('organizations/:organizationId/ripplebrain')
@UseGuards(JwtAuthGuard, EmailVerifiedGuard)
export class RippleBrainController {
  constructor(private readonly rippleBrainService: RippleBrainService) {}

  @Post('analyze')
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: 'Run a policy impact analysis for an organization' })
  @ApiResponse({ status: 200, description: 'Analysis with impacts, exceptions, and action drafts' })
  async analyze(
    @Request() req: { user: TokenPayload },
    @Param('organizationId') organizationId: string,
    @Body() data: AnalyzeRippleBrainDto,
  ): Promise<unknown> {
    return this.rippleBrainService.analyze(req.user.sub, organizationId, data);
  }

  @Post('actions/:actionId/approve')
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: 'Approve a RippleBrain action (OWNER or ADMIN)' })
  async approve(
    @Request() req: { user: TokenPayload },
    @Param('organizationId') organizationId: string,
    @Param('actionId') actionId: string,
    @Body() data: RippleBrainDecisionDto,
  ): Promise<unknown> {
    return this.rippleBrainService.approve(req.user.sub, organizationId, actionId, data);
  }

  @Post('actions/:actionId/reject')
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: 'Reject a RippleBrain action (OWNER or ADMIN)' })
  async reject(
    @Request() req: { user: TokenPayload },
    @Param('organizationId') organizationId: string,
    @Param('actionId') actionId: string,
    @Body() data: RippleBrainDecisionDto,
  ): Promise<unknown> {
    return this.rippleBrainService.reject(req.user.sub, organizationId, actionId, data);
  }

  @Get('runs')
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: 'List this organization’s RippleBrain audit trail' })
  async listRuns(
    @Request() req: { user: TokenPayload },
    @Param('organizationId') organizationId: string,
  ): Promise<unknown> {
    return this.rippleBrainService.listRuns(req.user.sub, organizationId);
  }
}
