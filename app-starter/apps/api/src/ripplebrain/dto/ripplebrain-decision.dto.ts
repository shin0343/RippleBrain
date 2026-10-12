import { IsOptional, IsString, MaxLength } from 'class-validator';

export class RippleBrainDecisionDto {
  @IsOptional()
  @IsString()
  @MaxLength(1000, { message: 'Note must be less than 1000 characters' })
  note?: string;
}
