import { Module } from '@nestjs/common';
import { PrismaModule } from '../prisma/prisma.module';
import { OrganizationsModule } from '../organizations/organizations.module';
import { RippleBrainController } from './ripplebrain.controller';
import { RippleBrainService } from './ripplebrain.service';

@Module({
  imports: [PrismaModule, OrganizationsModule],
  controllers: [RippleBrainController],
  providers: [RippleBrainService],
  exports: [RippleBrainService],
})
export class RippleBrainModule {}
