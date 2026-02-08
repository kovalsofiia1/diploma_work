import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule, NavController } from '@ionic/angular';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';

interface EventDetail {
  title: string;
  city: string;
  date: string;
  image: string;
  uid: string;
}

@Component({
  selector: 'app-event-detail',
  templateUrl: './event-detail.page.html',
  styleUrls: ['./event-detail.page.scss'],
  standalone: true,
  imports: [CommonModule, IonicModule, RouterModule],
})
export class EventDetailPage implements OnInit {
  uid: string = '';
  event?: EventDetail;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private navCtrl: NavController
  ) {}

  ngOnInit(): void {
    this.uid = this.route.snapshot.paramMap.get('uid') ?? '';
    // Prefer navigation state when available
    const state = (this.router.getCurrentNavigation()?.extras?.state as any) ?? {};
    this.event = state?.item ?? (history.state?.item as EventDetail | undefined);
  }

  back(): void {
    this.navCtrl.back();
  }
}


