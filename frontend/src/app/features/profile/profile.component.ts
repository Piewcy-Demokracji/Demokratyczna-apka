import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

interface OptionSet {
  name: string;
  optionsCount: number;
}

@Component({
  selector: 'app-profile',
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.css']
})
export class ProfileComponent implements OnInit {
  username = 'PlaceholderUser';
  profilePic = 'https://via.placeholder.com/100';

  optionSets: OptionSet[] = [
    { name: 'Coffee near me', optionsCount: 5 },
    { name: 'Best study spots', optionsCount: 4 },
    { name: 'Favorite lunch spots', optionsCount: 6 }
  ];

  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit(): void {
    if (this.authService.isLoggedIn()) {
      this.authService.whoAmI().subscribe({
        next: data => {
          this.username = data.username;
        },
        error: () => {
          this.username = this.authService.getCurrentUsername() || 'PlaceholderUser';
        }
      });
    }
  }

  editSet(set: OptionSet): void {
    console.log('Edit', set);
  }

  launchSet(set: OptionSet): void {
    console.log('Launch', set);
  }

  deleteSet(set: OptionSet): void {
    console.log('Delete', set);
  }

  addOptionSet(): void {
    console.log('Add new option set');
    const newSetName = `New set ${this.optionSets.length + 1}`;
    this.optionSets.push({ name: newSetName, optionsCount: 0 });
  }

  goHome(): void {
    this.router.navigate(['/']);
  }
}
